"""Backup integrity, restoration rollback, recovery and concurrency checks."""
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from paperbuilder.storage import Repository, demo_blueprint
from paperbuilder.blueprints import save_blueprint, load_blueprint
from paperbuilder.generation import generate_paper
from paperbuilder.papers import save_paper, load_paper, create_revision
from paperbuilder.backups import create_backup, prepare_restore, restore_backup, BackupError, TABLES


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.directory = Path(self.temp.name)
        self.repo = Repository(self.directory/'active.sqlite3'); self.repo.seed_demo()
        self.template = save_blueprint(self.repo, demo_blueprint())
        self.paper = generate_paper(demo_blueprint(), self.repo.questions(), True, 42)
        save_paper(self.repo, self.paper)
        self.revision = create_revision(self.repo, self.paper['paper_id']); save_paper(self.repo, self.revision)
        self.path = self.directory/'backup.sqlite3'

    def tearDown(self):
        self.repo.close(); self.temp.cleanup()

    @staticmethod
    def contents(connection):
        return {table: sorted([tuple(r) for r in connection.execute('SELECT * FROM '+table)], key=repr) for table in TABLES}

    def change_bank(self):
        q = self.repo.questions()[0]
        self.repo.update_question(q['id'], {'answer':'EDITED AFTER BACKUP'}, q['revision'])

    def test_backup_all_tables_and_exact_restoration_after_restart(self):
        before = self.contents(self.repo.connection)
        summary = create_backup(self.repo, self.path)
        self.assertEqual(summary, dict(questions=40, blueprints=1, blueprint_rows=6, papers=2, archived=0))
        self.change_bank()
        with prepare_restore(self.path, self.repo.path) as prepared:
            self.assertEqual(prepared.summary, summary)
            recovery = restore_backup(self.repo, prepared)
        self.assertTrue(recovery.is_file())
        self.assertEqual(self.contents(self.repo.connection), before)
        self.repo.close(); self.repo = Repository(self.directory/'active.sqlite3')
        self.assertFalse(self.repo.is_new)
        self.assertEqual(self.contents(self.repo.connection), before)
        self.assertEqual(load_paper(self.repo, self.paper['paper_id']), self.paper)
        self.assertEqual(load_paper(self.repo, self.revision['paper_id']), self.revision)
        self.assertEqual(load_blueprint(self.repo, self.template)['rows'], demo_blueprint()['rows'])

    def test_recovery_copy_restores_pre_restore_state(self):
        create_backup(self.repo, self.path); self.change_bank()
        before_restore = self.contents(self.repo.connection)
        with prepare_restore(self.path, self.repo.path) as prepared:
            recovery = restore_backup(self.repo, prepared)
        with prepare_restore(recovery, self.repo.path) as prepared:
            restore_backup(self.repo, prepared)
        self.assertEqual(self.contents(self.repo.connection), before_restore)

    def test_prepare_is_read_only_and_cancel_makes_no_changes(self):
        create_backup(self.repo, self.path); self.change_bank()
        before = self.contents(self.repo.connection); source = self.path.read_bytes()
        with prepare_restore(self.path, self.repo.path) as prepared:
            self.assertEqual(prepared.summary['papers'], 2)
        self.assertEqual(self.contents(self.repo.connection), before)
        self.assertEqual(self.path.read_bytes(), source)
        self.assertEqual(list(self.directory.glob('*.bak')), [])

    def test_preview_uses_private_snapshot_if_source_later_changes(self):
        create_backup(self.repo, self.path)
        with prepare_restore(self.path, self.repo.path) as prepared:
            original = self.contents(prepared.connection)
            self.path.write_bytes(b'CHANGED AFTER PREVIEW')
            restore_backup(self.repo, prepared)
        self.assertEqual(self.contents(self.repo.connection), original)

    def test_backup_never_overwrites_existing_destination(self):
        self.path.write_bytes(b'KEEP THIS')
        with self.assertRaises(BackupError): create_backup(self.repo, self.path)
        self.assertEqual(self.path.read_bytes(), b'KEEP THIS')

    def test_active_database_cannot_be_backup_or_restore_source(self):
        before = self.contents(self.repo.connection)
        with self.assertRaises(BackupError): create_backup(self.repo, self.repo.path)
        with self.assertRaises(BackupError), prepare_restore(self.repo.path, self.repo.path): pass
        self.assertEqual(self.contents(self.repo.connection), before)

    def test_invalid_extension_and_missing_destination_folder(self):
        for destination in (self.directory/'bad.txt', self.directory/'missing'/'backup.sqlite3'):
            with self.subTest(path=destination), self.assertRaises(BackupError): create_backup(self.repo, destination)
        self.assertFalse((self.directory/'bad.txt').exists())

    def test_invalid_files_and_versions_rejected_without_active_changes(self):
        before = self.contents(self.repo.connection)
        for content in (b'not a database', b'', b'SQLite format 3\0truncated'):
            self.path.write_bytes(content)
            with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass
        self.path.unlink()
        create_backup(self.repo, self.path)
        for version in (1, 3, 999):
            with sqlite3.connect(self.path) as connection: connection.execute('PRAGMA user_version='+str(version))
            with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass
        self.assertEqual(self.contents(self.repo.connection), before)

    def test_missing_and_oversized_source_rejected(self):
        with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass
        create_backup(self.repo, self.path)
        with patch('paperbuilder.backups.MAX_BYTES', 1):
            with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass

    def test_unknown_schema_and_extra_objects_rejected(self):
        create_backup(self.repo, self.path)
        with sqlite3.connect(self.path) as connection:
            connection.execute('CREATE TABLE unrelated(secret TEXT)')
        with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass

    def test_corrupt_saved_paper_rejected(self):
        create_backup(self.repo, self.path)
        with sqlite3.connect(self.path) as connection:
            connection.execute('DROP TRIGGER immutable_paper')
            connection.execute("UPDATE papers SET snapshot_json='broken'")
            connection.execute("CREATE TRIGGER immutable_paper BEFORE UPDATE ON papers BEGIN SELECT RAISE(ABORT,'immutable'); END")
        with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass

    def test_invalid_question_and_prompt_hash_rejected(self):
        create_backup(self.repo, self.path)
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE questions SET prompt_hash='wrong' WHERE id='PY-001'")
        with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass

    def test_noninteger_question_revision_rejected(self):
        create_backup(self.repo, self.path)
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE questions SET revision=1.5 WHERE id='PY-001'")
        with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass

    def test_blueprint_row_gap_and_orphan_rejected(self):
        create_backup(self.repo, self.path)
        with sqlite3.connect(self.path) as connection:
            connection.execute('UPDATE blueprint_rows SET position=99 WHERE position=6')
        with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass
        self.path.unlink(); create_backup(self.repo, self.path)
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE blueprint_rows SET blueprint_id='MISSING'")
        with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass

    def test_missing_revision_parent_rejected(self):
        create_backup(self.repo, self.path)
        with sqlite3.connect(self.path) as connection:
            connection.execute('DELETE FROM papers WHERE id=?', (self.paper['paper_id'],))
        with self.assertRaises(BackupError), prepare_restore(self.path, self.repo.path): pass

    def test_failed_recovery_backup_prevents_any_restore_changes(self):
        create_backup(self.repo, self.path); self.change_bank()
        before = self.contents(self.repo.connection)
        with prepare_restore(self.path, self.repo.path) as prepared:
            with patch('paperbuilder.backups._copy', side_effect=OSError('disk full')):
                with self.assertRaisesRegex(BackupError, 'rolled back'):
                    restore_backup(self.repo, prepared)
        self.assertEqual(self.contents(self.repo.connection), before)
        self.assertFalse(self.repo.connection.in_transaction)

    def test_insert_failure_after_deletion_rolls_back_all_tables(self):
        create_backup(self.repo, self.path); self.change_bank()
        before = self.contents(self.repo.connection)
        self.repo.connection.execute("CREATE TRIGGER fail_restore BEFORE INSERT ON questions WHEN NEW.id='PY-002' BEGIN SELECT RAISE(ABORT,'injected'); END")
        with prepare_restore(self.path, self.repo.path) as prepared:
            with self.assertRaisesRegex(BackupError, 'Recovery copy'):
                restore_backup(self.repo, prepared)
        self.assertEqual(self.contents(self.repo.connection), before)
        self.assertEqual(len(list(self.directory.glob('*.bak'))), 1)
        self.assertFalse(self.repo.connection.in_transaction)

    def test_busy_writer_rejects_restore_without_changes(self):
        create_backup(self.repo, self.path)
        other = Repository(self.repo.path)
        self.repo.connection.execute('PRAGMA busy_timeout=1')
        before = self.contents(self.repo.connection)
        try:
            with prepare_restore(self.path, self.repo.path) as prepared:
                other.connection.execute('BEGIN IMMEDIATE')
                with self.assertRaises(BackupError): restore_backup(self.repo, prepared)
        finally:
            other.connection.rollback(); other.close()
        self.assertEqual(self.contents(self.repo.connection), before)

    def test_wal_backup_includes_committed_changes(self):
        self.repo.connection.execute('PRAGMA journal_mode=WAL')
        self.change_bank()
        before = self.contents(self.repo.connection)
        create_backup(self.repo, self.path)
        with prepare_restore(self.path, self.repo.path) as prepared:
            self.assertEqual(self.contents(prepared.connection), before)
            restore_backup(self.repo, prepared)
        self.assertEqual(self.contents(self.repo.connection), before)

    def test_empty_database_restores_without_reseeding(self):
        empty = Repository(self.directory/'empty.sqlite3')
        try: create_backup(empty, self.path)
        finally: empty.close()
        with prepare_restore(self.path, self.repo.path) as prepared: restore_backup(self.repo, prepared)
        self.repo.close(); self.repo = Repository(self.directory/'active.sqlite3')
        self.assertFalse(self.repo.is_new)
        self.assertEqual(self.repo.questions(), [])

    def test_cli_startup_does_not_reseed_existing_empty_database(self):
        empty = Repository(self.directory/'empty.sqlite3'); empty.close()
        result = subprocess.run([sys.executable, 'main.py', '--check', '--db', str(self.directory/'empty.sqlite3')],
                                capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent)
        self.assertEqual(result.returncode, 1)
        empty = Repository(self.directory/'empty.sqlite3')
        try: self.assertEqual(empty.questions(), [])
        finally: empty.close()

    def test_archive_review_and_unicode_survive_backup(self):
        q = self.repo.questions()[0]
        q = self.repo.update_question(q['id'], {'answer':'Unicode café ₹\n    keep indentation'}, q['revision'])
        q = self.repo.approve_question(q['id'], q['revision'], 'Teacher')
        self.repo.set_archived(q['id'], True, q['revision'])
        original = self.contents(self.repo.connection)
        create_backup(self.repo, self.path)
        with prepare_restore(self.path, self.repo.path) as prepared:
            self.assertEqual(prepared.summary['archived'], 1)
            restore_backup(self.repo, prepared)
        self.assertEqual(self.contents(self.repo.connection), original)

    def test_failed_backup_does_not_leave_published_or_temporary_file(self):
        with patch('paperbuilder.backups._copy', side_effect=OSError('disk full')):
            with self.assertRaises(BackupError): create_backup(self.repo, self.path)
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.directory.glob('.qpb-*')), [])


if __name__ == '__main__': unittest.main()
