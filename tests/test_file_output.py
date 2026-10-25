"""Regression coverage for Windows write-access requirements during fsync."""
from pathlib import Path
import errno
import os
import tempfile
import unittest
from unittest.mock import patch
from paperbuilder.file_output import staged_output
from paperbuilder.storage import Repository, demo_blueprint
from paperbuilder.backups import create_backup, prepare_restore, restore_backup
from paperbuilder.generation import generate_paper
from paperbuilder.pdf_export import export_pdf


_REAL_FSYNC = os.fsync


def windows_style_fsync(fd):
    # A zero-byte write checks write access without changing the file. Windows
    # _commit/FlushFileBuffers needs a writable handle; POSIX fsync can accept rb.
    os.write(fd, b'')
    _REAL_FSYNC(fd)


class FileOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.directory = Path(self.temp.name)
        self.destination = self.directory/'result.bin'

    def tearDown(self):
        self.temp.cleanup()

    def test_flush_has_write_access_and_preserves_complete_content(self):
        payload = b'Complete output\x00\xff\n' * 100
        with patch('paperbuilder.file_output.os.fsync', side_effect=windows_style_fsync) as flush:
            with staged_output(self.destination) as temporary:
                temporary.write_bytes(payload)
        flush.assert_called_once()
        self.assertEqual(self.destination.read_bytes(), payload)
        self.assertEqual(list(self.directory.glob('.qpb-*')), [])

    def test_new_file_flush_failure_leaves_no_output(self):
        with patch('paperbuilder.file_output.os.fsync', side_effect=OSError(errno.EIO, 'Flush failed')):
            with self.assertRaises(OSError), staged_output(self.destination) as temporary:
                temporary.write_bytes(b'new content')
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.directory.glob('.qpb-*')), [])

    def test_overwrite_flush_failure_preserves_existing_file(self):
        self.destination.write_bytes(b'original')
        with patch('paperbuilder.file_output.os.fsync', side_effect=OSError(errno.EIO, 'Flush failed')):
            with self.assertRaises(OSError), staged_output(self.destination, overwrite=True) as temporary:
                temporary.write_bytes(b'replacement')
        self.assertEqual(self.destination.read_bytes(), b'original')

    def test_publish_failure_removes_new_reservation(self):
        with patch('paperbuilder.file_output.os.replace', side_effect=PermissionError('Cannot publish')):
            with self.assertRaises(PermissionError), staged_output(self.destination) as temporary:
                temporary.write_bytes(b'new content')
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.directory.glob('.qpb-*')), [])

    def test_successful_overwrite_with_windows_flush(self):
        self.destination.write_bytes(b'old output longer than replacement')
        with patch('paperbuilder.file_output.os.fsync', side_effect=windows_style_fsync):
            with staged_output(self.destination, overwrite=True) as temporary:
                temporary.write_bytes(b'new')
        self.assertEqual(self.destination.read_bytes(), b'new')

    def test_database_backup_and_restore_recovery_with_windows_flush(self):
        repo = Repository(self.directory/'active.sqlite3'); repo.seed_demo()
        backup = self.directory/'backup.sqlite3'
        try:
            original = repo.questions()
            with patch('paperbuilder.file_output.os.fsync', side_effect=windows_style_fsync):
                create_backup(repo, backup)
                q = repo.questions()[0]
                repo.update_question(q['id'], {'answer':'changed after backup'}, q['revision'])
                with prepare_restore(backup, repo.path) as prepared:
                    recovery = restore_backup(repo, prepared)
            self.assertEqual(repo.questions(), original)
            self.assertTrue(recovery.is_file())
            with prepare_restore(recovery, repo.path) as prepared:
                self.assertEqual(prepared.summary['questions'], 40)
        finally:
            repo.close()

    def test_pdf_exports_with_windows_flush(self):
        try:
            import reportlab
        except ImportError:
            self.skipTest('Install requirements.txt for PDF export regression check')
        repo = Repository(self.directory/'active.sqlite3'); repo.seed_demo()
        try:
            paper = generate_paper(demo_blueprint(), repo.questions(), True, 42)
            with patch('paperbuilder.file_output.os.fsync', side_effect=windows_style_fsync):
                for teacher in (False, True):
                    destination = self.directory/('teacher.pdf' if teacher else 'student.pdf')
                    export_pdf(paper, destination, teacher=teacher)
                    self.assertTrue(destination.read_bytes().startswith(b'%PDF-'))
        finally:
            repo.close()


if __name__ == '__main__': unittest.main()
