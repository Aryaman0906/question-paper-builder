"""Phase 2 acceptance tests: persisted state, review and all-or-nothing imports."""
from copy import deepcopy
from io import StringIO
from pathlib import Path
import csv
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from paperbuilder.storage import Repository, BankError, ROOT, demo_blueprint
from paperbuilder.validation import availability
from paperbuilder.csv_import import (HEADERS, parse_csv, read_preview, commit_preview,
                                     attach_bank_errors, save_template)


def question(identifier='USR-1', **changes):
    q = dict(id=identifier, subject='Python Programming', unit='Module 1', topic='Types',
             kind='Short answer', marks=2, difficulty='Easy',
             prompt='Explain the type of ' + identifier + '.', answer='A model answer.',
             rubric='One mark for the type; one for the explanation.', options=[], correct_option_id=None)
    q.update(changes)
    return q


def csv_text(questions, headers=HEADERS):
    out = StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=headers)
    writer.writeheader()
    for q in questions:
        row = {key: q.get(key, '') for key in HEADERS[:10]}
        for key in 'ABCD':
            row['option_' + key.lower()] = next((o['text'] for o in q.get('options', []) if o['id'] == key), '')
        row['correct_option'] = q.get('correct_option_id') or ''
        writer.writerow({k: row.get(k, '') for k in headers})
    return out.getvalue()


class BankTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'bank.sqlite3'
        self.repo = Repository(self.path)

    def tearDown(self):
        self.repo.close()
        self.temp.cleanup()

    def preview(self, questions):
        p = parse_csv(csv_text(questions))
        attach_bank_errors(p, self.repo)
        return p

    def test_new_question_is_draft_and_persists_after_restart(self):
        q = self.repo.create_question(question(review_status='approved', is_demo=True, active=False))
        self.assertEqual((q['review_status'], q['is_demo'], q['active']), ('draft', False, True))
        self.repo.close(); self.repo = Repository(self.path)
        self.assertEqual(self.repo.get(q['id'])['prompt'], q['prompt'])

    def test_invalid_create_changes_nothing(self):
        for changes in ({'marks': 0}, {'marks': True}, {'answer': ' '}, {'id': 'bad id'}, {'kind': 'Essay'}):
            with self.subTest(changes=changes), self.assertRaises(BankError):
                self.repo.create_question(question(**changes))
        self.assertEqual(self.repo.questions(), [])

    def test_duplicate_prompt_normalizes_unicode_and_newlines(self):
        self.repo.create_question(question(prompt='café\r\n    print(1)'))
        with self.assertRaises(BankError):
            self.repo.create_question(question('USR-2', prompt='  cafe\u0301\n    print(1)\n'))
        self.assertEqual(len(self.repo.questions()), 1)

    def test_distinct_indentation_and_case_are_preserved(self):
        a = self.repo.create_question(question(prompt='if True:\n    print(Name)'))
        b = self.repo.create_question(question('USR-2', prompt='if True:\n  print(name)'))
        self.assertNotEqual(a['prompt_hash'], b['prompt_hash'])

    def test_approval_noop_then_content_edit(self):
        q = self.repo.create_question(question())
        q = self.repo.approve_question(q['id'], q['revision'], 'Teacher')
        self.assertIn('Teacher', q['review_note'])
        unchanged = self.repo.update_question(q['id'], deepcopy(q), q['revision'])
        self.assertEqual(unchanged, q)
        saved = self.repo.update_question(q['id'], {'answer': 'Revised answer', 'id': 'CHANGED'}, q['revision'])
        self.assertEqual(saved['id'], q['id'])
        self.assertEqual(saved['review_status'], 'draft')
        self.assertEqual(saved['revision'], q['revision'] + 1)

    def test_reviewer_name_required(self):
        q = self.repo.create_question(question())
        with self.assertRaises(BankError):
            self.repo.approve_question(q['id'], q['revision'], ' ')
        self.assertEqual(self.repo.get(q['id'])['review_status'], 'draft')

    def test_stale_edit_from_second_connection_does_not_overwrite(self):
        q = self.repo.create_question(question())
        other = Repository(self.path)
        try:
            other.update_question(q['id'], {'answer': 'Other window saved this'}, q['revision'])
            with self.assertRaisesRegex(BankError, 'changed in another window'):
                self.repo.update_question(q['id'], {'answer': 'Stale content'}, q['revision'])
        finally:
            other.close()
        self.assertEqual(self.repo.get(q['id'])['answer'], 'Other window saved this')

    def test_duplicate_edit_preserves_original_and_approval(self):
        first = self.repo.create_question(question())
        second = self.repo.create_question(question('USR-2'))
        second = self.repo.approve_question(second['id'], second['revision'], 'Teacher')
        with self.assertRaises(BankError):
            self.repo.update_question(second['id'], {'prompt': first['prompt']}, second['revision'])
        self.assertEqual(self.repo.get(second['id']), second)

    def test_archive_restore_requires_review_and_reserves_id(self):
        q = self.repo.create_question(question())
        q = self.repo.approve_question(q['id'], q['revision'], 'Teacher')
        q = self.repo.set_archived(q['id'], True, q['revision'])
        with self.assertRaises(BankError):
            self.repo.create_question(question(prompt='Different text'))
        with self.assertRaises(BankError):
            self.repo.update_question(q['id'], {'answer': 'edit'}, q['revision'])
        with self.assertRaises(BankError):
            self.repo.approve_question(q['id'], q['revision'], 'Teacher')
        q = self.repo.set_archived(q['id'], False, q['revision'])
        self.assertTrue(q['active'])
        self.assertEqual(q['review_status'], 'draft')

    def test_restore_duplicate_is_rejected(self):
        q = self.repo.create_question(question())
        q = self.repo.set_archived(q['id'], True, q['revision'])
        self.repo.create_question(question('USR-2', prompt=q['prompt']))
        with self.assertRaises(BankError):
            self.repo.set_archived(q['id'], False, q['revision'])
        self.assertFalse(self.repo.get(q['id'])['active'])

    def test_demo_origin_survives_edit_approval_and_reseed(self):
        self.repo.seed_demo()
        q = self.repo.get('PY-001')
        q = self.repo.update_question(q['id'], {'answer': 'Changed answer'}, q['revision'])
        q = self.repo.approve_question(q['id'], q['revision'], 'Teacher')
        self.repo.seed_demo()
        self.assertEqual(self.repo.get(q['id']), q)
        self.assertTrue(q['is_demo'])
        report = availability(demo_blueprint(), self.repo.questions(), include_demo=False)
        self.assertTrue(all(g['available'] == 0 for g in report['groups']))

    def test_drafts_and_archived_are_excluded_from_availability(self):
        q = self.repo.create_question(question())
        bp = demo_blueprint()
        supply = lambda: sum(g['available'] for g in availability(bp, self.repo.questions())['groups'])
        self.assertEqual(supply(), 0)
        q = self.repo.approve_question(q['id'], q['revision'], 'Teacher')
        self.assertEqual(supply(), 1)
        self.repo.set_archived(q['id'], True, q['revision'])
        self.assertEqual(supply(), 0)

    def test_preview_does_not_write_and_valid_import_is_all_drafts(self):
        p = self.preview([question(), question('USR-2')])
        self.assertTrue(p.ready)
        self.assertEqual(self.repo.questions(), [])
        self.assertEqual(commit_preview(p, self.repo), 2)
        self.assertTrue(all(q['review_status'] == 'draft' and not q['is_demo'] for q in self.repo.questions()))

    def test_invalid_row_blocks_entire_import(self):
        p = self.preview([question(), question('USR-2', marks=-1)])
        self.assertFalse(p.ready)
        self.assertTrue(p.rows[1].errors)
        with self.assertRaises(BankError): commit_preview(p, self.repo)
        self.assertEqual(self.repo.questions(), [])

    def test_batch_checks_duplicate_ids_and_prompts(self):
        for second in (question(prompt='A different prompt'), question('USR-2', prompt=question()['prompt'])):
            p = self.preview([question(), second])
            self.assertFalse(p.ready)
            self.assertTrue(p.rows[1].errors)
        self.assertEqual(self.repo.questions(), [])

    def test_reimport_is_rejected(self):
        questions = [question(), question('USR-2')]
        commit_preview(self.preview(questions), self.repo)
        self.assertFalse(self.preview(questions).ready)
        self.assertEqual(len(self.repo.questions()), 2)

    def test_stale_preview_revalidates_before_any_insert(self):
        p = self.preview([question(), question('USR-2')])
        self.repo.create_question(question('USR-2'))
        with self.assertRaises(BankError): commit_preview(p, self.repo)
        self.assertEqual([q['id'] for q in self.repo.questions()], ['USR-2'])

    def test_database_error_mid_batch_rolls_back_first_row(self):
        self.repo.connection.execute("""CREATE TRIGGER fail_second BEFORE INSERT ON questions
            WHEN NEW.id = 'USR-2' BEGIN SELECT RAISE(ABORT, 'Simulated failure'); END""")
        p = self.preview([question(), question('USR-2')])
        with self.assertRaises(BankError): commit_preview(p, self.repo)
        self.assertEqual(self.repo.questions(), [])

    def test_direct_batch_validation_is_atomic(self):
        with self.assertRaises(BankError):
            self.repo.import_questions([question(), question('USR-2', marks=0)])
        self.assertEqual(self.repo.questions(), [])

    def test_utf8_file_and_bad_encoding(self):
        path = Path(self.temp.name) / 'import.csv'
        path.write_text(csv_text([question(prompt='Explain café and Unicode.')]), encoding='utf-8-sig')
        self.assertTrue(read_preview(path, self.repo).ready)
        path.write_bytes(b'\xff\xfe\x00\x01')
        self.assertFalse(read_preview(path, self.repo).ready)
        with patch('paperbuilder.csv_import.MAX_BYTES', 8):
            path.write_bytes(b'x' * 9)
            self.assertIn('2 MiB', read_preview(path, self.repo).errors[0])

    def test_template_is_header_only_with_expected_columns(self):
        path = Path(self.temp.name) / 'template.csv'
        save_template(path)
        rows = list(csv.reader(StringIO(path.read_text(encoding='utf-8-sig'))))
        self.assertEqual(rows, [list(HEADERS)])


class CsvFormatTests(unittest.TestCase):
    def test_multiline_quotes_commas_and_unicode_roundtrip(self):
        q = question(prompt='What does "café, tea" mean?\nExplain.', answer='if ready:\n    print("yes, go")')
        text = csv_text([q])
        p = parse_csv(text)
        self.assertTrue(p.ready, p.errors)
        self.assertEqual(p.rows[0].question['prompt'], q['prompt'])
        self.assertEqual(p.rows[0].question['answer'], q['answer'])
        self.assertEqual(p.rows[0].line, len(text.splitlines()))

    def test_mcq_mapping_and_invalid_options(self):
        q = question(kind='MCQ', options=[dict(id=k, text=str(i)) for i,k in enumerate('ABCD')], correct_option_id='B')
        p = parse_csv(csv_text([q]))
        self.assertTrue(p.ready)
        self.assertEqual(p.rows[0].question['correct_option_id'], 'B')
        q['options'][1]['text'] = q['options'][0]['text']
        self.assertFalse(parse_csv(csv_text([q])).ready)
        q['options'][1]['text'] = '1'; q['correct_option_id'] = 'E'
        self.assertFalse(parse_csv(csv_text([q])).ready)

    def test_non_mcq_rejects_options(self):
        self.assertFalse(parse_csv(csv_text([question(options=[dict(id='A', text='No')])])).ready)
        self.assertFalse(parse_csv(csv_text([question(correct_option_id='A')])).ready)

    def test_exact_headers_but_reordering_supported(self):
        self.assertTrue(parse_csv(csv_text([question()], tuple(reversed(HEADERS)))).ready)
        for headers in (HEADERS[:-1], HEADERS + ('unexpected',), HEADERS + ('id',)):
            p = parse_csv(csv_text([], headers))
            self.assertFalse(p.ready)
            self.assertTrue(p.errors)

    def test_malformed_quotes_and_column_counts(self):
        header = csv_text([])
        for text in (header + '"unfinished', header + 'too,few\n', header + ','.join(['x'] * 16)):
            p = parse_csv(text)
            self.assertFalse(p.ready)
            self.assertTrue(p.errors or p.rows[0].errors)

    def test_empty_blank_nul_and_nontext_are_rejected(self):
        for text in ('', csv_text([]), '\x00', None, csv_text([]) + ',' * 14 + '\n'):
            self.assertFalse(parse_csv(text).ready)

    def test_marks_are_positive_whole_ascii_numbers(self):
        for value in ('1.5', '-2', '1e3', 'True', '0', '９', '1' * 20):
            with self.subTest(value=value):
                self.assertFalse(parse_csv(csv_text([question(marks=value)])).ready)

    def test_limits_apply_to_nonempty_records(self):
        with patch('paperbuilder.csv_import.MAX_ROWS', 2):
            text = csv_text([question(), question('USR-2')]) + ',' * 14 + '\n'
            p = parse_csv(text)
            self.assertTrue(p.ready)
            self.assertEqual(p.skipped_blank, 1)
            self.assertFalse(parse_csv(csv_text([question(), question('USR-2'), question('USR-3')])).ready)
        with patch('paperbuilder.csv_import.MAX_BYTES', 8):
            self.assertFalse(parse_csv('x' * 9).ready)


class MigrationTests(unittest.TestCase):
    def test_version_one_backup_and_upgrade_preserve_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'old.sqlite3'
            schema = (ROOT / 'paperbuilder' / 'schema.sql').read_text(encoding='utf-8')
            schema = schema.replace('    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),\n', '').replace('user_version = 2', 'user_version = 1')
            old = sqlite3.connect(path)
            old.executescript(schema)
            old.execute("""INSERT INTO questions
                (id,subject,unit,kind,marks,difficulty,prompt,answer,rubric,prompt_hash,active)
                VALUES ('OLD','Python','M1','Coding',4,'Hard','Original','answer','rubric','hash',0)""")
            old.commit(); old.close()
            repo = Repository(path)
            backup = repo.migration_backup
            try:
                q = repo.get('OLD')
                self.assertEqual((q['prompt'], q['active'], q['revision']), ('Original', False, 1))
                self.assertEqual(repo.connection.execute('PRAGMA user_version').fetchone()[0], 2)
                self.assertTrue(backup.exists())
                with sqlite3.connect(backup) as saved:
                    self.assertEqual(saved.execute('PRAGMA user_version').fetchone()[0], 1)
                    self.assertEqual(saved.execute('SELECT prompt FROM questions').fetchone()[0], 'Original')
            finally: repo.close()
            repo = Repository(path)
            try: self.assertIsNone(repo.migration_backup)
            finally: repo.close()
            self.assertEqual(len(list(Path(directory).glob('*.bak'))), 1)

    def test_newer_database_version_is_not_modified(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'newer.sqlite3'
            with sqlite3.connect(path) as conn:
                conn.execute('PRAGMA user_version=99')
            before = path.read_bytes()
            with self.assertRaisesRegex(BankError, 'Unsupported'): Repository(path)
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
