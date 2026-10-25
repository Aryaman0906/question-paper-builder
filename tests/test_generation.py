"""Phase 3: exact selection, independent verification and saved templates."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest
from paperbuilder.storage import Repository, BankError, demo_blueprint
from paperbuilder.validation import blueprint_errors, availability
from paperbuilder.blueprints import save_blueprint, list_blueprints, load_blueprint
from paperbuilder.generation import generate_paper, paper_errors, preview_text, GenerationError


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'bank.sqlite3'
        self.repo=Repository(self.path);self.repo.seed_demo()
        self.bank=self.repo.questions();self.bp=demo_blueprint()

    def tearDown(self):
        self.repo.close();self.temp.cleanup()

    def generate(self,**kwargs):
        return generate_paper(kwargs.pop('bp',self.bp),kwargs.pop('bank',self.bank),include_demo=kwargs.pop('include_demo',True),**kwargs)

    @staticmethod
    def ids(p):return [i['question']['id'] for i in p['items']]

    def test_demo_exact_marks_rows_units_and_uniqueness(self):
        p=self.generate(seed=7)
        self.assertEqual(paper_errors(p),[])
        self.assertEqual(p['summary'],dict(total_marks=40,question_count=13,difficulty_marks=dict(Easy=12,Medium=20,Hard=8),unit_marks={'Module 1':18,'Module 2':22}))
        self.assertEqual(len(set(self.ids(p))),13)
        self.assertEqual([i['row_index'] for i in p['items']],[0]*3+[1]*3+[2]*2+[3]*3+[4]+[5])

    def test_many_seeds_preserve_every_constraint(self):
        selections=set()
        for seed in range(100):
            p=self.generate(seed=seed);self.assertEqual(paper_errors(p),[]);selections.add(tuple(self.ids(p)))
        self.assertGreater(len(selections),1)

    def test_same_seed_stable_despite_bank_order_and_global_rng(self):
        first=self.generate(seed=12)
        random.seed(813);[random.random() for _ in range(20)]
        second=self.generate(seed=12,bank=list(reversed(self.bank)))
        self.assertEqual(self.ids(first),self.ids(second))
        self.assertEqual(first['items'],second['items'])

    def test_generator_does_not_change_global_rng(self):
        before=random.getstate();self.generate(seed=1);self.assertEqual(random.getstate(),before)

    def test_blank_seed_is_recorded_and_reproducible(self):
        p=self.generate();self.assertIs(type(p['seed']),int)
        self.assertEqual(self.ids(p),self.ids(self.generate(seed=p['seed'])))

    def test_invalid_seed_or_mode_is_rejected(self):
        for seed in (-1,2**63,True,'7',1.5):
            with self.subTest(seed=seed),self.assertRaises(GenerationError):self.generate(seed=seed)
        with self.assertRaises(GenerationError):self.generate(include_demo='yes')

    def test_production_mode_excludes_demo_even_if_approved(self):
        with self.assertRaisesRegex(GenerationError,'available 0'):generate_paper(self.bp,self.bank)
        for q in self.bank:q['review_status']='approved'
        with self.assertRaises(GenerationError):self.generate(include_demo=False)

    def test_production_approved_bank_generates_without_demo_label(self):
        for q in self.bank:q.update(is_demo=False,review_status='approved')
        p=self.generate(include_demo=False)
        self.assertFalse(p['is_demo']);self.assertEqual(paper_errors(p),[])
        self.assertNotIn('DEMONSTRATION ONLY',preview_text(p))

    def test_draft_and_archived_questions_are_excluded(self):
        for q in self.bank:
            if q['unit']=='Module 1' and q['difficulty']=='Hard':q.update(active=False)
        with self.assertRaisesRegex(GenerationError,'need 1, available 0, add 1'):self.generate()
        for q in self.bank:q.update(active=True,review_status='draft')
        with self.assertRaises(GenerationError):self.generate()

    def test_repeated_group_across_sections_never_reuses_question(self):
        self.bp['rows'].insert(1,dict(self.bp['rows'][0],section='A2',count=2))
        self.bp['rows'][0]['count']=1
        p=self.generate(seed=5)
        self.assertEqual(paper_errors(p),[]);self.assertEqual(len(set(self.ids(p))),13)
        self.assertEqual([i['section'] for i in p['items'][:3]],['A','A2','A2'])

    def test_shortage_aggregates_repeated_rows(self):
        row=self.bp['rows'][0]
        self.bp['rows']=[dict(row,count=4),dict(row,section='B',count=3)]
        self.bp.update(total_marks=14,difficulty_percent=dict(Easy=100,Medium=0,Hard=0))
        with self.assertRaisesRegex(GenerationError,'need 7, available 6, add 1'):self.generate()

    def test_invalid_blueprint_not_silently_rebalanced(self):
        for changes in ({'total_marks':41},{'difficulty_percent':dict(Easy=33,Medium=47,Hard=20)},{'rows':[]}):
            bp=deepcopy(self.bp);bp.update(changes)
            with self.subTest(changes=changes),self.assertRaises(GenerationError):self.generate(bp=bp)
        self.assertEqual(self.bp,demo_blueprint())

    def test_snapshots_do_not_mutate_or_follow_bank_and_blueprint(self):
        original_bank=deepcopy(self.bank);original_bp=deepcopy(self.bp)
        p=self.generate(seed=3)
        self.assertEqual(self.bank,original_bank);self.assertEqual(self.bp,original_bp)
        self.bank[0]['answer']='MODIFIED';self.bp['title']='CHANGED'
        self.assertNotEqual(p['blueprint']['title'],'CHANGED')
        self.assertTrue(all(i['question']['answer']!='MODIFIED' for i in p['items']))

    def test_identical_input_duplicates_deduplicated_conflicting_rejected(self):
        self.bank.append(deepcopy(self.bank[0]));p=self.generate(seed=1)
        self.assertEqual(len(set(self.ids(p))),13)
        self.bank[-1]['answer']='conflict'
        with self.assertRaisesRegex(GenerationError,'Conflicting'):self.generate()

    def test_eligible_malformed_mcq_blocks_generation(self):
        q=next(q for q in self.bank if q['kind']=='MCQ');q['correct_option_id']='missing'
        with self.assertRaisesRegex(GenerationError,'needs correction'):self.generate()

    def test_postcheck_catches_tampering(self):
        original=self.generate(seed=1)
        changes=[lambda p:p['items'][0]['question'].update(marks=99),
                 lambda p:p['items'][0]['question'].update(review_status='draft'),
                 lambda p:p['items'][0].update(section='WRONG'),
                 lambda p:p['items'][0].update(number=True),
                 lambda p:p['items'][0].update(row_index=-1),
                 lambda p:p['items'][0]['question'].update(id=p['items'][1]['question']['id']),
                 lambda p:p['summary'].update(total_marks=1),
                 lambda p:p['items'].pop(),lambda p:p.update(is_demo=False),
                 lambda p:p['items'].reverse()]
        for i,change in enumerate(changes):
            p=deepcopy(original);change(p)
            with self.subTest(change=i):self.assertTrue(paper_errors(p))

    def test_mcq_options_and_answer_key_separation(self):
        q=next(q for q in self.bank if q['kind']=='MCQ')
        q.update(answer='SECRET_ANSWER_ONLY',rubric='SECRET_RUBRIC_ONLY')
        bp=dict(title='MCQ paper',subject=q['subject'],instructions='Answer every question.',duration_minutes=10,total_marks=q['marks'],
                difficulty_percent=dict(Easy=100,Medium=0,Hard=0),rows=[dict(section='A',unit=q['unit'],kind='MCQ',difficulty='Easy',marks=q['marks'],count=1)])
        p=self.generate(bp=bp,bank=[q],seed=0)
        student=preview_text(p);teacher=preview_text(p,teacher=True)
        for secret in ('SECRET_ANSWER_ONLY','SECRET_RUBRIC_ONLY',q['id'],'Correct option:','Seed:'):
            self.assertNotIn(secret,student)
        self.assertIn('SECRET_ANSWER_ONLY',teacher);self.assertIn('SECRET_RUBRIC_ONLY',teacher)
        for option in q['options']:self.assertIn(option['text'],student)
        self.assertIn('DEMONSTRATION ONLY',student)

    def test_invalid_preview_is_refused(self):
        p=self.generate();p['items'].clear()
        with self.assertRaises(GenerationError):preview_text(p)

    def test_invalid_shapes_and_limits_return_errors(self):
        for bp in (None,[],{},dict(self.bp,instructions=9),dict(self.bp,rows=self.bp['rows']*20)):
            self.assertTrue(blueprint_errors(bp))
        bp=deepcopy(self.bp);bp['rows']=[dict(bp['rows'][0],count=1001)]
        self.assertTrue(any('1,000' in e for e in blueprint_errors(bp)))
        for p in (None,{},dict(blueprint=self.bp,is_demo=True,items=None)):
            self.assertTrue(paper_errors(p))

    def test_generation_does_not_write_bank_or_papers(self):
        before=self.repo.questions();self.generate()
        self.assertEqual(before,self.repo.questions())
        self.assertEqual(self.repo.connection.execute('SELECT count(*) FROM papers').fetchone()[0],0)


class BlueprintStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'db.sqlite3'
        self.repo=Repository(self.path);self.bp=demo_blueprint()

    def tearDown(self):self.repo.close();self.temp.cleanup()

    def test_save_load_after_reopen_preserves_rows_instructions_targets(self):
        self.bp['instructions']='Show code:\n    preserve indentation — café'
        identifier=save_blueprint(self.repo,self.bp)
        self.repo.close();self.repo=Repository(self.path)
        loaded=load_blueprint(self.repo,identifier)
        self.assertEqual(loaded['id'],identifier)
        self.assertEqual(loaded['rows'],self.bp['rows'])
        self.assertEqual(loaded['instructions'],self.bp['instructions'])
        self.assertEqual(loaded['difficulty_percent'],{d:str(v) for d,v in self.bp['difficulty_percent'].items()})
        self.assertEqual(list_blueprints(self.repo)[0]['id'],identifier)

    def test_save_creates_new_copy_without_overwriting(self):
        first=save_blueprint(self.repo,self.bp)
        self.bp['title']='Changed title';second=save_blueprint(self.repo,self.bp)
        self.assertNotEqual(first,second)
        self.assertNotEqual(load_blueprint(self.repo,first)['title'],load_blueprint(self.repo,second)['title'])
        self.assertEqual(list_blueprints(self.repo)[0]['id'],second)

    def test_invalid_blueprint_leaves_database_empty(self):
        self.bp['rows'][0]['count']=0
        with self.assertRaises(BankError):save_blueprint(self.repo,self.bp)
        self.assertEqual(list_blueprints(self.repo),[])
        self.assertEqual(self.repo.connection.execute('SELECT count(*) FROM blueprint_rows').fetchone()[0],0)

    def test_mid_save_failure_rolls_back_header_and_all_rows(self):
        self.repo.connection.execute("""CREATE TRIGGER fail_second_row BEFORE INSERT ON blueprint_rows
            WHEN NEW.position=2 BEGIN SELECT RAISE(ABORT,'Injected failure'); END""")
        with self.assertRaises(BankError):save_blueprint(self.repo,self.bp)
        self.assertEqual(list_blueprints(self.repo),[])
        self.assertEqual(self.repo.connection.execute('SELECT count(*) FROM blueprint_rows').fetchone()[0],0)

    def test_missing_or_corrupted_saved_blueprint_rejected(self):
        with self.assertRaises(BankError):load_blueprint(self.repo,'missing')
        identifier=save_blueprint(self.repo,self.bp)
        with self.repo.connection:self.repo.connection.execute('UPDATE blueprints SET targets_json=? WHERE id=?',('bad json',identifier))
        with self.assertRaises(BankError):load_blueprint(self.repo,identifier)
        self.assertFalse(self.repo.connection.in_transaction)

    def test_partial_saved_rows_rejected(self):
        identifier=save_blueprint(self.repo,self.bp)
        with self.repo.connection:self.repo.connection.execute('DELETE FROM blueprint_rows WHERE blueprint_id=? AND position=2',(identifier,))
        with self.assertRaises(BankError):load_blueprint(self.repo,identifier)

    def test_existing_schema_two_used_without_migration_or_bank_loss(self):
        self.repo.seed_demo();before=self.repo.questions()
        save_blueprint(self.repo,self.bp)
        self.assertEqual(self.repo.questions(),before)
        self.assertEqual(self.repo.connection.execute('PRAGMA user_version').fetchone()[0],2)
        self.assertIsNone(self.repo.migration_backup)

    def test_decimal_targets_saved_as_lossless_strings(self):
        self.bp['difficulty_percent']={d:Decimal(str(v)) for d,v in self.bp['difficulty_percent'].items()}
        identifier=save_blueprint(self.repo,self.bp)
        self.assertEqual(blueprint_errors(load_blueprint(self.repo,identifier)),[])


if __name__=='__main__':unittest.main()
