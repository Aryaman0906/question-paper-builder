"""Functional checks for the foundation milestone, not a completed application."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from paperbuilder.storage import Repository, ROOT, demo_blueprint
from paperbuilder.validation import availability, blueprint_errors, question_errors, prompt_hash


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'demo.sqlite3'
        self.repo = Repository(self.path)
        self.repo.seed_demo()
        self.bp = demo_blueprint()

    def tearDown(self):
        self.repo.close();self.temp.cleanup()

    def test_sample_bank_valid(self):
        questions=self.repo.questions()
        self.assertEqual(len(questions),40)
        for q in questions:self.assertEqual(question_errors(q),[],q['id'])

    def test_demo_blueprint_exact_totals(self):
        self.assertEqual(blueprint_errors(self.bp),[])
        self.assertEqual(sum(r['marks']*r['count'] for r in self.bp['rows']),40)
        self.assertEqual(sum(r['count'] for r in self.bp['rows']),13)
        report=availability(self.bp,self.repo.questions(),include_demo=True)
        self.assertTrue(report['valid'])
        self.assertEqual([g['available'] for g in report['groups']],[6,6,8,8,4,4])

    def test_demo_questions_excluded_by_default(self):
        report=availability(self.bp,self.repo.questions())
        self.assertFalse(report['valid'])
        self.assertTrue(all(g['available']==0 for g in report['groups']))

    def test_reseed_idempotent_and_preserves_edits(self):
        self.repo.connection.execute("UPDATE questions SET answer = ? WHERE id = ?",('An existing edit','PY-001'))
        self.repo.connection.commit()
        self.assertEqual(self.repo.seed_demo(),0)
        self.assertEqual(self.repo.questions()[0]['answer'],'An existing edit')
        self.assertEqual(len(self.repo.questions()),40)

    def test_repeated_groups_aggregate_across_sections(self):
        row=self.bp['rows'][0];row['count']=1
        second=deepcopy(row);second['count']=2;second['section']='D'
        self.bp['rows'].append(second)
        report=availability(self.bp,self.repo.questions(),True)
        self.assertEqual(len(report['groups']),6)
        self.assertEqual(report['groups'][0]['required'],3)

    def test_real_shortage(self):
        qs=[q for q in self.repo.questions() if not(q['unit']=='Module 1' and q['difficulty']=='Hard')]
        report=availability(self.bp,qs,True)
        self.assertFalse(report['valid'])
        self.assertEqual(sum(g['shortage'] for g in report['groups']),1)

    def test_duplicate_ids_do_not_inflate_availability(self):
        qs=self.repo.questions()
        self.assertEqual(availability(self.bp,qs,True),availability(self.bp,qs+qs,True))

    def test_bad_percentages_rejected(self):
        for value in (-1,101,'NaN','Infinity','abc'):
            bp=deepcopy(self.bp);bp['difficulty_percent']['Easy']=value
            self.assertTrue(blueprint_errors(bp))
        self.bp['difficulty_percent']['Easy']=31
        self.assertIn('Difficulty percentages must total 100.',blueprint_errors(self.bp))

    def test_fractional_targets_and_wrong_totals_rejected(self):
        self.bp['total_marks']=41
        errors=blueprint_errors(self.bp)
        self.assertTrue(any('whole-mark' in e for e in errors))
        self.assertTrue(any('Rows allocate' in e for e in errors))

    def test_invalid_row_and_marks(self):
        for value in (0,-1,True,2.5,'2'):
            bp=deepcopy(self.bp);bp['rows'][0]['marks']=value
            self.assertTrue(blueprint_errors(bp))
        q=self.repo.questions()[0];q['marks']=0
        self.assertTrue(question_errors(q))

    def test_mcq_mapping_and_duplicates(self):
        q=next(q for q in self.repo.questions() if q['kind']=='MCQ')
        q['correct_option_id']='Z';self.assertTrue(question_errors(q))
        q['correct_option_id']='B';q['options'][1]['text']=q['options'][0]['text']
        self.assertTrue(question_errors(q))

    def test_database_enforces_marks_and_duplicates(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.connection.execute('UPDATE questions SET marks=0 WHERE id=?',('PY-001',))
        self.repo.connection.rollback()
        hashed=self.repo.questions()[0]['prompt_hash']
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.connection.execute('UPDATE questions SET prompt_hash=? WHERE id=?',(hashed,'PY-002'))
        self.repo.connection.rollback()
        self.assertEqual(self.repo.connection.execute('PRAGMA foreign_keys').fetchone()[0],1)

    def test_snapshot_schema_is_immutable(self):
        self.repo.connection.execute('INSERT INTO papers(id,title,app_version,snapshot_json,is_demo) VALUES(?,?,?,?,?)',('p1','Demo','0.1.0','{"questions":[]}',1))
        self.repo.connection.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.connection.execute('UPDATE papers SET title=? WHERE id=?',('Changed','p1'))
        self.repo.connection.rollback()

    def test_bank_survives_restart(self):
        second=Repository(self.path)
        try:self.assertEqual(len(second.questions()),40)
        finally:second.close()

    def test_code_whitespace_preserved(self):
        self.assertNotEqual(prompt_hash('if x:\n    f()'),prompt_hash('if x:\nf()'))
        self.assertNotEqual(prompt_hash('print(X)'),prompt_hash('print(x)'))
        self.assertEqual(prompt_hash(' a\r\nb '),prompt_hash('a\nb'))

    def test_trusted_sample_coding_answers(self):
        # Only our bundled authored answers are executed for QA, never user imports.
        questions={q['id']:q for q in self.repo.questions()}
        fixtures=json.loads((ROOT/'data'/'trusted_answer_fixtures.json').read_text())
        for fixture in fixtures:
            namespace={};exec(questions[fixture['question_id']]['answer'],namespace)
            for value,expected in zip(fixture['inputs'],fixture['expected']):
                original=deepcopy(value)
                result=namespace['solve'](value)
                self.assertEqual(json.loads(json.dumps(result)),expected,fixture['question_id'])
                self.assertEqual(value,original)
        file_path=Path(self.temp.name)/'words.txt'
        file_path.write_text(' one two\n\n three \n',encoding='utf-8')
        ns={};exec(questions['PY-033']['answer'],ns)
        self.assertEqual(ns['solve'](file_path),3)
        self.assertEqual(ns['solve'](Path(self.temp.name)/'missing'),0)
        ns={};exec(questions['PY-034']['answer'],ns)
        self.assertEqual(ns['solve'](file_path),['one two','three'])
        ns={};exec(questions['PY-036']['answer'],ns)
        self.assertEqual(ns['solve'](file_path,'hello'),6)
        self.assertEqual(file_path.read_text(encoding='utf-8'),' one two\n\n three \nhello\n')


if __name__=='__main__':unittest.main()
