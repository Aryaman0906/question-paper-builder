"""Rendered PDF content, page bounds and failed-output preservation."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from paperbuilder.storage import Repository, demo_blueprint
from paperbuilder.generation import generate_paper
from paperbuilder.papers import save_paper, load_paper
from paperbuilder.pdf_export import export_pdf, export_blocks, ExportError

try:
    import reportlab
    import pdfplumber
    from pypdf import PdfReader
except ImportError:
    reportlab = None


@unittest.skipUnless(reportlab is not None, 'Install requirements-dev.txt for PDF verification')
class PdfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.directory = Path(self.temp.name)
        self.repo = Repository(self.directory/'data.sqlite3'); self.repo.seed_demo()
        self.paper = generate_paper(demo_blueprint(), self.repo.questions(), True, 42)
        self.path = self.directory/'paper.pdf'

    def tearDown(self):
        self.repo.close(); self.temp.cleanup()

    def text(self, path=None):
        return '\n'.join(page.extract_text() for page in PdfReader(path or self.path).pages)

    def test_student_pdf_contains_questions_not_teacher_fields_or_metadata(self):
        self.paper['items'][0]['question'].update(answer='UNIQUE_SECRET_ANSWER', rubric='UNIQUE_SECRET_RUBRIC')
        export_pdf(self.paper, self.path)
        text = self.text()
        self.assertIn('Python demonstration paper', text)
        self.assertIn('Total marks: 40', text)
        self.assertIn('Question 13', text)
        for secret in ('UNIQUE_SECRET', 'Initial seed:', self.paper['paper_id'], 'Balance by marks', 'Marking guidance', 'Model answer'):
            self.assertNotIn(secret, text)
            self.assertNotIn(secret, str(PdfReader(self.path).metadata))
        self.assertIn('STUDENT QUESTION PAPER', text)

    def test_teacher_key_has_answers_rubrics_and_balances(self):
        self.paper['items'][0]['question'].update(answer='UNIQUE_SECRET_ANSWER', rubric='UNIQUE_SECRET_RUBRIC')
        export_pdf(self.paper, self.path, teacher=True)
        text = self.text()
        for expected in ('UNIQUE_SECRET_ANSWER', 'UNIQUE_SECRET_RUBRIC', 'Balance by marks', 'Easy: 12', 'Medium: 20', 'Hard: 8', 'Module 1: 18', 'Initial seed: 42', self.paper['paper_id']):
            self.assertIn(expected, text)

    def test_a4_pages_have_audience_demo_labels_and_page_numbers(self):
        for teacher in (False, True):
            export_pdf(self.paper, self.path, teacher=teacher, overwrite=self.path.exists())
            for number, page in enumerate(PdfReader(self.path).pages, 1):
                self.assertAlmostEqual(float(page.mediabox.width), 595.2756, places=2)
                self.assertAlmostEqual(float(page.mediabox.height), 841.8898, places=2)
                text = page.extract_text()
                self.assertIn('DEMONSTRATION ONLY', text); self.assertIn(f'Page {number}', text)
                self.assertIn('TEACHER ANSWER KEY' if teacher else 'STUDENT QUESTION PAPER', text)

    def test_reexport_after_reopen_has_same_printed_text(self):
        export_pdf(self.paper, self.path, teacher=True)
        expected = self.text()
        identifier = save_paper(self.repo, self.paper)
        self.repo.close(); self.repo = Repository(self.directory/'data.sqlite3')
        export_pdf(load_paper(self.repo, identifier), self.path, teacher=True, overwrite=True)
        self.assertEqual(self.text(), expected)

    def test_literal_markup_and_special_characters_are_not_interpreted(self):
        self.paper['items'][0]['question']['prompt'] = '<img src="file:///DO_NOT_READ"/> & <b>literal</b>'
        export_pdf(self.paper, self.path)
        self.assertIn('<img src="file:///DO_NOT_READ"/> & <b>literal</b>', self.text())
        self.assertEqual(len(PdfReader(self.path).pages[0].images), 0)

    def test_long_multiline_code_is_paginated_without_margin_overflow(self):
        coding = next(i['question'] for i in self.paper['items'] if i['question']['kind']=='Coding')
        coding['answer'] = 'def solve(n):\n' + '\n'.join('    print("' + str(i) + ' ' + 'x'*130 + '")' for i in range(100)) + '\n    return n'
        export_pdf(self.paper, self.path, teacher=True)
        reader = PdfReader(self.path)
        self.assertGreater(len(reader.pages), 3)
        self.assertIn('return n', self.text())
        self.assertIn('> ', self.text())
        with pdfplumber.open(self.path) as document:
            for page in document.pages:
                for char in page.chars:
                    self.assertGreaterEqual(char['x0'], 47)
                    self.assertLessEqual(char['x1'], float(page.width)-47)
                    self.assertGreater(char['top'], 18)
                    self.assertLess(char['bottom'], float(page.height)-20)

    def test_code_indentation_has_visible_offsets(self):
        coding = next(i['question'] for i in self.paper['items'] if i['question']['kind']=='Coding')
        coding['answer'] = 'def UNIQUE_FUNCTION(n):\n    UNIQUE_INDENT = n\n    return UNIQUE_INDENT'
        export_pdf(self.paper, self.path, teacher=True)
        with pdfplumber.open(self.path) as document:
            words = [word for page in document.pages for word in page.extract_words()]
        first = next(w for w in words if 'UNIQUE_FUNCTION' in w['text'])
        indented = next(w for w in words if w['text']=='UNIQUE_INDENT')
        # Function identifier follows "def "; compare to the start of that line.
        function_start = first['x0'] - 4 * 5.418
        self.assertGreater(indented['x0'], function_start + 15)

    def test_mcq_options_export_without_correct_option_in_student(self):
        bank = self.repo.questions(); q = next(q for q in bank if q['kind']=='MCQ')
        bp = demo_blueprint(); bp.update(total_marks=2, difficulty_percent=dict(Easy=100, Medium=0, Hard=0),
            rows=[dict(section='A', unit=q['unit'], kind='MCQ', marks=2, difficulty='Easy', count=1)])
        paper = generate_paper(bp, bank, True, 1)
        export_pdf(paper, self.path)
        text = self.text()
        for option in paper['items'][0]['question']['options']: self.assertIn(option['text'], text)
        self.assertNotIn('Correct option:', text)
        export_pdf(paper, self.path, teacher=True, overwrite=True)
        self.assertIn('Correct option:', self.text())

    def test_invalid_snapshot_and_invalid_audience_write_nothing(self):
        changed = deepcopy(self.paper); changed['summary']['total_marks'] = 1
        for paper, teacher in ((changed, False), (self.paper, 'teacher')):
            with self.assertRaises(ExportError): export_pdf(paper, self.path, teacher=teacher)
        self.assertFalse(self.path.exists())

    def test_existing_pdf_requires_explicit_overwrite(self):
        export_pdf(self.paper, self.path)
        before = self.path.read_bytes()
        with self.assertRaises(ExportError): export_pdf(self.paper, self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_non_pdf_file_is_protected_even_with_overwrite(self):
        self.path.write_bytes(b'PRIVATE DATABASE OR OTHER FILE')
        with self.assertRaises(ExportError): export_pdf(self.paper, self.path, overwrite=True)
        self.assertEqual(self.path.read_bytes(), b'PRIVATE DATABASE OR OTHER FILE')
        with self.assertRaises(ExportError): export_pdf(self.paper, self.directory/'bad.sqlite3')

    def test_failed_build_preserves_existing_pdf_and_cleans_temporary(self):
        self.path.write_bytes(b'%PDF-existing data')
        def fail(*args):
            Path(args[2]).write_bytes(b'partial output')
            raise OSError('disk full')
        with patch('paperbuilder.pdf_export._build_pdf', side_effect=fail):
            with self.assertRaises(ExportError): export_pdf(self.paper, self.path, overwrite=True)
        self.assertEqual(self.path.read_bytes(), b'%PDF-existing data')
        self.assertEqual(list(self.directory.glob('.qpb-*')), [])

    def test_missing_reportlab_has_actionable_error_and_keeps_paper(self):
        before = deepcopy(self.paper)
        with patch.dict('sys.modules', {'reportlab': None}):
            with self.assertRaisesRegex(ExportError, 'pip install'):
                export_pdf(self.paper, self.path)
        self.assertEqual(self.paper, before); self.assertFalse(self.path.exists())

    def test_unsupported_script_fails_clearly_without_publishing(self):
        self.paper['blueprint']['title'] = 'हिन्दी परीक्षा'
        with self.assertRaisesRegex(ExportError, 'does not yet support'):
            export_pdf(self.paper, self.path)
        self.assertFalse(self.path.exists())

    def test_student_export_does_not_process_teacher_only_unicode(self):
        self.paper['items'][0]['question']['answer'] = 'हिन्दी'
        export_pdf(self.paper, self.path)
        with self.assertRaises(ExportError): export_pdf(self.paper, self.directory/'teacher.pdf', teacher=True)

    def test_latin_unicode_export_and_production_label(self):
        self.paper['blueprint']['title'] = 'Café - résumé'
        for item in self.paper['items']: item['question'].update(is_demo=False, review_status='approved')
        self.paper['is_demo'] = False
        export_pdf(self.paper, self.path)
        self.assertIn('Café - résumé', self.text())
        self.assertNotIn('DEMONSTRATION', self.text())

    def test_bundled_fonts_fallback_exports_demo_without_system_fonts(self):
        original = Path.is_file
        def bundled_only(path):
            return original(path) and path.name not in ('segoeui.ttf','consola.ttf','DejaVuSans.ttf','DejaVuSansMono.ttf')
        with patch.object(Path, 'is_file', bundled_only):
            export_pdf(self.paper, self.path, teacher=True)
        self.assertIn('Question 13', self.text())

    def test_export_leaves_input_and_database_unchanged(self):
        before = deepcopy(self.paper); changes = self.repo.connection.total_changes
        export_pdf(self.paper, self.path, teacher=True)
        self.assertEqual(self.paper, before)
        self.assertEqual(self.repo.connection.total_changes, changes)


if __name__ == '__main__': unittest.main()
