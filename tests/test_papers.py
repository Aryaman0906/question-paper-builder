"""Phase 4 regression tests: immutable history, revisions and replacement races."""
from copy import deepcopy
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from paperbuilder.storage import Repository, BankError, demo_blueprint
from paperbuilder.generation import generate_paper, preview_text, paper_errors
from paperbuilder.papers import (save_paper, load_paper, list_papers, create_revision,
                                replacement_candidates, replace_question, validate_snapshot)


class PaperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'bank.sqlite3'
        self.repo = Repository(self.path); self.repo.seed_demo()
        self.paper = generate_paper(demo_blueprint(), self.repo.questions(), True, 42)

    def tearDown(self):
        self.repo.close(); self.temp.cleanup()

    def candidate(self, paper=None, number=1):
        return replacement_candidates(paper or self.paper, number, self.repo.questions())[0]

    def test_save_restart_exact_student_and_teacher_snapshots(self):
        original = deepcopy(self.paper)
        student, teacher = preview_text(original), preview_text(original, True)
        identifier = save_paper(self.repo, self.paper)
        self.repo.close(); self.repo = Repository(self.path)
        loaded = load_paper(self.repo, identifier)
        self.assertEqual(loaded, original)
        self.assertEqual(preview_text(loaded), student)
        self.assertEqual(preview_text(loaded, True), teacher)
        self.assertEqual(self.repo.connection.execute('PRAGMA user_version').fetchone()[0], 2)

    def test_bank_edit_archive_and_missing_record_do_not_change_saved_paper(self):
        identifier = save_paper(self.repo, self.paper)
        q = self.paper['items'][0]['question']
        updated = self.repo.update_question(q['id'], {'answer':'NEW ANSWER'}, q['revision'])
        self.repo.set_archived(q['id'], True, updated['revision'])
        with self.repo.connection:
            self.repo.connection.execute('DELETE FROM questions WHERE id=?', (q['id'],))
        self.assertEqual(load_paper(self.repo, identifier), self.paper)

    def test_save_and_load_are_independent_copies(self):
        original = deepcopy(self.paper); identifier = save_paper(self.repo, self.paper)
        self.paper['items'][0]['question']['answer'] = 'changed caller'
        loaded = load_paper(self.repo, identifier); loaded['blueprint']['title'] = 'changed read'
        self.assertEqual(load_paper(self.repo, identifier), original)

    def test_retry_save_is_idempotent_across_connections(self):
        save_paper(self.repo, self.paper)
        other = Repository(self.path)
        try:
            self.assertEqual(save_paper(other, deepcopy(self.paper)), self.paper['paper_id'])
            self.assertEqual(len(list_papers(other)), 1)
        finally:
            other.close()

    def test_existing_id_content_cannot_be_overwritten(self):
        identifier = save_paper(self.repo, self.paper)
        altered = deepcopy(self.paper); altered['items'][0]['question']['answer'] = 'different'
        with self.assertRaisesRegex(BankError, 'already saved'):
            save_paper(self.repo, altered)
        self.assertEqual(load_paper(self.repo, identifier), self.paper)

    def test_sql_update_trigger_protects_snapshot(self):
        identifier = save_paper(self.repo, self.paper)
        with self.assertRaises(sqlite3.IntegrityError), self.repo.connection:
            self.repo.connection.execute("UPDATE papers SET title='changed' WHERE id=?", (identifier,))
        self.assertEqual(load_paper(self.repo, identifier), self.paper)

    def test_injected_insert_failure_rolls_back_and_can_retry(self):
        self.repo.connection.execute("CREATE TRIGGER fail_save BEFORE INSERT ON papers BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(BankError):
            save_paper(self.repo, self.paper)
        self.assertEqual(list_papers(self.repo), [])
        self.assertFalse(self.repo.connection.in_transaction)
        self.repo.connection.execute('DROP TRIGGER fail_save')
        save_paper(self.repo, self.paper)
        self.assertEqual(len(list_papers(self.repo)), 1)

    def test_locked_database_keeps_unsaved_input_for_retry(self):
        original = deepcopy(self.paper)
        other = Repository(self.path)
        self.repo.connection.execute('PRAGMA busy_timeout=1')
        try:
            other.connection.execute('BEGIN IMMEDIATE')
            with self.assertRaises(BankError):
                save_paper(self.repo, self.paper)
            self.assertEqual(self.paper, original)
        finally:
            other.connection.rollback(); other.close()
        self.assertEqual(list_papers(self.repo), [])
        save_paper(self.repo, self.paper)

    def test_invalid_envelopes_and_selection_never_write(self):
        changes = [lambda p:p.update(schema_version=2), lambda p:p.update(schema_version=True),
                   lambda p:p.update(paper_id='bad'), lambda p:p.update(app_version=''),
                   lambda p:p.update(created_at='bad'), lambda p:p.update(created_at='2026-10-25T00:00:00'),
                   lambda p:p.update(seed=True), lambda p:p.update(seed=-1),
                   lambda p:p.update(parent_paper_id=p['paper_id']), lambda p:p.update(parent_paper_id='bad'),
                   lambda p:p.update(replacement_count=-1), lambda p:p.update(replacement_count=True),
                   lambda p:p['items'][0]['question'].update(active=1),
                   lambda p:p['items'][0]['question'].pop('options'),
                   lambda p:p['summary'].update(total_marks=1), lambda p:p['items'].pop(),
                   lambda p:p.update(extra=float('nan'))]
        for change in changes:
            altered = deepcopy(self.paper); change(altered)
            with self.subTest(paper=altered.get('paper_id')), self.assertRaises(BankError):
                save_paper(self.repo, altered)
        self.assertEqual(list_papers(self.repo), [])

    def test_bad_shapes_produce_recoverable_errors(self):
        for value in (None, [], {}, {'schema_version':1}):
            with self.subTest(value=value), self.assertRaises(BankError):
                validate_snapshot(value)

    def test_missing_saved_paper(self):
        with self.assertRaisesRegex(BankError, 'no longer exists'):
            load_paper(self.repo, 'P-' + '0'*32)

    def insert_corrupt(self, raw, **metadata):
        p = self.paper
        fields = dict(id=p['paper_id'], title=p['blueprint']['title'], schema_version=1,
                      app_version=p['app_version'], is_demo=1, created_at=p['created_at'])
        fields.update(metadata)
        with self.repo.connection:
            self.repo.connection.execute('DELETE FROM papers')
            self.repo.connection.execute('INSERT INTO papers (id,title,schema_version,app_version,snapshot_json,is_demo,created_at) VALUES (?,?,?,?,?,?,?)',
                (fields['id'],fields['title'],fields['schema_version'],fields['app_version'],raw,fields['is_demo'],fields['created_at']))

    def test_corrupt_json_duplicate_fields_and_unknown_version_block_open(self):
        for raw in ('{', 'null', '[]', '{"a":1,"a":2}', '{"a":NaN}',
                    json.dumps(dict(self.paper, schema_version=99)),
                    json.dumps(dict(self.paper, items=None))):
            self.insert_corrupt(raw)
            with self.subTest(raw=raw[:40]), self.assertRaises(BankError):
                load_paper(self.repo, self.paper['paper_id'])

    def test_metadata_mismatch_blocks_open(self):
        for metadata in ({'title':'wrong'}, {'is_demo':0}, {'app_version':'wrong'}, {'schema_version':9}, {'created_at':'wrong'}):
            self.insert_corrupt(json.dumps(self.paper), **metadata)
            with self.subTest(metadata=metadata), self.assertRaises(BankError):
                load_paper(self.repo, self.paper['paper_id'])

    def test_history_sorted_and_same_title_records_retained(self):
        save_paper(self.repo, self.paper)
        later = generate_paper(demo_blueprint(), self.repo.questions(), True, 7)
        save_paper(self.repo, later)
        rows = list_papers(self.repo)
        self.assertEqual([r['id'] for r in rows], [later['paper_id'], self.paper['paper_id']])
        self.assertEqual(rows[0]['title'], rows[1]['title'])

    def test_revision_is_unsaved_new_identity_with_exact_parent_content(self):
        identifier = save_paper(self.repo, self.paper)
        revision = create_revision(self.repo, identifier)
        self.assertNotEqual(revision['paper_id'], identifier)
        self.assertEqual(revision['parent_paper_id'], identifier)
        self.assertEqual(revision['items'], self.paper['items'])
        self.assertEqual(len(list_papers(self.repo)), 1)
        save_paper(self.repo, revision)
        self.assertEqual(load_paper(self.repo, identifier), self.paper)
        self.assertEqual(load_paper(self.repo, revision['paper_id']), revision)

    def test_revision_chain_and_sibling_revisions_are_separate(self):
        parent = save_paper(self.repo, self.paper)
        a, b = create_revision(self.repo, parent), create_revision(self.repo, parent)
        save_paper(self.repo, a); save_paper(self.repo, b)
        child = create_revision(self.repo, a['paper_id']); save_paper(self.repo, child)
        self.assertEqual(child['parent_paper_id'], a['paper_id'])
        self.assertEqual(len(list_papers(self.repo)), 4)
        self.assertEqual(load_paper(self.repo, parent), self.paper)

    def test_missing_parent_cannot_be_saved(self):
        self.paper['parent_paper_id'] = 'P-' + '0'*32
        with self.assertRaises(BankError):
            save_paper(self.repo, self.paper)
        self.assertEqual(list_papers(self.repo), [])

    def test_revision_preserves_blueprint_mode_and_seed(self):
        identifier = save_paper(self.repo, self.paper)
        for field in ('seed', 'blueprint'):
            revision = create_revision(self.repo, identifier)
            if field == 'seed': revision['seed'] += 1
            else: revision['blueprint']['title'] = 'changed'
            with self.assertRaisesRegex(BankError, 'preserve'):
                save_paper(self.repo, revision)
        self.assertEqual(len(list_papers(self.repo)), 1)

    def test_all_slots_offer_only_exact_unused_candidates(self):
        used = {i['question']['id'] for i in self.paper['items']}
        bank = self.repo.questions()
        for number, item in enumerate(self.paper['items'], 1):
            old = item['question']
            candidates = replacement_candidates(self.paper, number, bank)
            self.assertTrue(candidates)
            for q in candidates:
                self.assertNotIn(q['id'], used)
                self.assertEqual(tuple(q[k] for k in ('subject','unit','kind','marks','difficulty')),
                                 tuple(old[k] for k in ('subject','unit','kind','marks','difficulty')))

    def test_each_slot_replacement_preserves_balance_and_other_questions(self):
        original = deepcopy(self.paper)
        for number in range(1, 14):
            candidate = self.candidate(number=number)
            updated = replace_question(self.repo, self.paper, number, candidate)
            self.assertEqual(updated['items'][number-1]['question'], candidate)
            self.assertEqual(updated['summary'], self.paper['summary'])
            self.assertEqual(updated['blueprint'], self.paper['blueprint'])
            self.assertEqual(updated['replacement_count'], 1)
            self.assertEqual(paper_errors(updated), [])
            for i in range(13):
                if i != number-1: self.assertEqual(updated['items'][i], self.paper['items'][i])
        self.assertEqual(self.paper, original)

    def test_replacements_in_revision_preserve_saved_original(self):
        identifier = save_paper(self.repo, self.paper)
        revision = create_revision(self.repo, identifier)
        revision = replace_question(self.repo, revision, 1, self.candidate(revision))
        save_paper(self.repo, revision)
        self.assertEqual(load_paper(self.repo, identifier), self.paper)
        self.assertNotEqual(load_paper(self.repo, revision['paper_id'])['items'], self.paper['items'])
        teacher = preview_text(revision, True)
        self.assertIn('before any replacements', teacher)
        self.assertIn('Replacements: 1', teacher)

    def test_cannot_replace_directly_in_saved_paper(self):
        save_paper(self.repo, self.paper)
        with self.assertRaisesRegex(BankError, 'read-only'):
            replace_question(self.repo, self.paper, 1, self.candidate())

    def test_stale_candidate_content_or_archive_rejected(self):
        for archive in (False, True):
            candidate = self.candidate()
            other = Repository(self.path)
            try:
                if archive: other.set_archived(candidate['id'], True, candidate['revision'])
                else: other.update_question(candidate['id'], {'answer':'Changed after preview'}, candidate['revision'])
            finally:
                other.close()
            with self.assertRaisesRegex(BankError, 'no longer available'):
                replace_question(self.repo, self.paper, 1, candidate)
        self.assertNotIn('replacement_count', self.paper)

    def test_review_only_revision_change_requires_new_preview(self):
        candidate = self.candidate()
        self.repo.approve_question(candidate['id'], candidate['revision'], 'Teacher')
        with self.assertRaises(BankError):
            replace_question(self.repo, self.paper, 1, candidate)
        refreshed = next(q for q in replacement_candidates(self.paper, 1, self.repo.questions()) if q['id'] == candidate['id'])
        self.assertEqual(paper_errors(replace_question(self.repo, self.paper, 1, refreshed)), [])

    def test_duplicate_used_wrong_group_and_invalid_number_rejected(self):
        for candidate in (self.paper['items'][0]['question'], self.paper['items'][-1]['question']):
            with self.assertRaises(BankError):
                replace_question(self.repo, self.paper, 1, candidate)
        for number in (0, 14, -1, True, '1'):
            with self.assertRaises(BankError):
                replacement_candidates(self.paper, number, self.repo.questions())

    def test_no_alternatives_does_not_relax_constraints(self):
        bank = [i['question'] for i in self.paper['items']]
        self.assertEqual(replacement_candidates(self.paper, 1, bank), [])

    def test_production_candidates_exclude_demo_draft_archive(self):
        bank = self.repo.questions()
        for q in bank: q.update(is_demo=False, review_status='approved')
        paper = generate_paper(demo_blueprint(), bank, False, 42)
        candidates = replacement_candidates(paper, 1, bank)
        self.assertEqual(len(candidates), 3)
        for q, change in zip(candidates, ({'is_demo':True}, {'review_status':'draft'}, {'active':False})):
            next(record for record in bank if record['id']==q['id']).update(change)
        self.assertEqual(replacement_candidates(paper, 1, bank), [])

    def test_candidate_lists_are_copies_and_conflicting_ids_rejected(self):
        bank = self.repo.questions(); original = deepcopy(bank)
        candidates = replacement_candidates(self.paper, 1, bank)
        candidates[0]['answer'] = 'changed'
        self.assertEqual(bank, original)
        bank.append(deepcopy(bank[0])); replacement_candidates(self.paper, 1, bank)
        bank[-1]['answer'] = 'conflict'
        with self.assertRaises(BankError): replacement_candidates(self.paper, 1, bank)

    def test_replaced_student_preview_has_no_teacher_metadata(self):
        candidate = self.candidate(); candidate['answer'] = 'SECRET ANSWER'; candidate['rubric'] = 'SECRET RUBRIC'
        changed = self.repo.update_question(candidate['id'], {'answer':candidate['answer'], 'rubric':candidate['rubric']}, candidate['revision'])
        self.repo.approve_question(changed['id'], changed['revision'], 'Teacher')
        updated = replace_question(self.repo, self.paper, 1, self.repo.get(candidate['id']))
        student, teacher = preview_text(updated), preview_text(updated, True)
        for secret in ('SECRET ANSWER', 'SECRET RUBRIC'):
            self.assertNotIn(secret, student); self.assertIn(secret, teacher)
        self.assertIn('DEMONSTRATION ONLY', student); self.assertIn('DEMONSTRATION ONLY', teacher)


if __name__ == '__main__':
    unittest.main()
