"""SQLite repository with atomic bank writes and a versioned migration."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sqlite3
from .validation import question_errors, prompt_hash

ROOT = Path(__file__).resolve().parent.parent
CONTENT_FIELDS = ('subject', 'unit', 'topic', 'kind', 'marks', 'difficulty',
                  'prompt', 'answer', 'rubric', 'options', 'correct_option_id')


class BankError(ValueError):
    """A recoverable validation, duplicate or stale-edit error."""


def default_database_path():
    base = Path(os.environ['LOCALAPPDATA']) if os.environ.get('LOCALAPPDATA') else Path.home() / '.local' / 'share'
    # Keep the Phase 1 path so upgrading does not hide existing work.
    return base / 'QuestionPaperBuilder' / 'demo_v1.sqlite3'


def new_question(question):
    q = {key: deepcopy(question.get(key)) for key in ('id',) + CONTENT_FIELDS}
    for field in ('id', 'subject', 'unit', 'topic'):
        if isinstance(q.get(field), str):
            q[field] = q[field].strip()
    q['topic'] = q.get('topic') or ''
    q['options'] = q.get('options') if q.get('options') is not None else []
    q['correct_option_id'] = q.get('correct_option_id') or None
    q.update(review_status='draft', review_note='Awaiting teacher review.',
             is_demo=False, active=True)
    return q


class Repository:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=5)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys = ON')
        self.migration_backup = None
        try:
            version = self.connection.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, 2):
                raise BankError(f'Unsupported database version {version}; no changes made.')
            if version == 0:
                schema = (ROOT / 'paperbuilder' / 'schema.sql').read_text(encoding='utf-8')
                self.connection.executescript('BEGIN IMMEDIATE;\n' + schema + '\nCOMMIT;')
            elif version == 1:
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                backup_path = self.path.with_name(self.path.name + '.before-v2-' + stamp + '.bak')
                destination = sqlite3.connect(backup_path)
                try:
                    self.connection.backup(destination)
                finally:
                    destination.close()
                with self.connection:
                    self.connection.execute('BEGIN IMMEDIATE')
                    self.connection.execute('ALTER TABLE questions ADD COLUMN revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0)')
                    self.connection.execute('PRAGMA user_version = 2')
                self.migration_backup = backup_path
        except Exception:
            self.connection.rollback()
            self.connection.close()
            raise

    def close(self):
        self.connection.close()

    @contextmanager
    def _write(self):
        try:
            with self.connection:
                self.connection.execute('BEGIN IMMEDIATE')
                yield
        except sqlite3.IntegrityError as exc:
            raise BankError('The change conflicts with an existing ID or active question. Refresh the bank and check for duplicates.') from exc
        except sqlite3.OperationalError as exc:
            raise BankError('The database could not be updated. Close other copies of the app, check the folder permissions, and try again.') from exc

    def _insert(self, q):
        self.connection.execute('''INSERT INTO questions
            (id,subject,unit,topic,kind,marks,difficulty,prompt,answer,rubric,
             options_json,correct_option_id,review_status,review_note,is_demo,active,prompt_hash)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (q['id'],q['subject'],q['unit'],q.get('topic',''),q['kind'],q['marks'],q['difficulty'],
             q['prompt'],q['answer'],q['rubric'],json.dumps(q.get('options', []), ensure_ascii=False),
             q.get('correct_option_id'),q['review_status'],q.get('review_note',''),
             int(q['is_demo']),int(q.get('active',True)),prompt_hash(q['prompt'])))

    @staticmethod
    def _decode(row):
        q = dict(row)
        q['options'] = json.loads(q.pop('options_json'))
        q['is_demo'] = bool(q['is_demo'])
        q['active'] = bool(q['active'])
        return q

    def get(self, question_id):
        row = self.connection.execute('SELECT * FROM questions WHERE id = ?', (question_id,)).fetchone()
        if row is None:
            raise BankError('This question no longer exists. Refresh the bank.')
        return self._decode(row)

    def questions(self):
        return [self._decode(row) for row in self.connection.execute('SELECT * FROM questions ORDER BY id')]

    def _duplicate(self, q, exclude_id=None):
        row = self.connection.execute('''SELECT id FROM questions
            WHERE subject = ? AND prompt_hash = ? AND active = 1 AND id != ?''',
            (q['subject'], prompt_hash(q['prompt']), exclude_id or '')).fetchone()
        return row['id'] if row else None

    def _require_valid(self, q):
        errors = question_errors(q)
        if errors:
            raise BankError('\n'.join(errors))

    def _current(self, question_id, revision):
        q = self.get(question_id)
        if type(revision) is not int or q['revision'] != revision:
            raise BankError('This question changed in another window. Reopen it before saving; your entries have been kept.')
        return q

    def create_question(self, question):
        q = new_question(question)
        self._require_valid(q)
        with self._write():
            if self.connection.execute('SELECT 1 FROM questions WHERE id=?',(q['id'],)).fetchone():
                raise BankError(f"Question ID {q['id']} already exists, including archived records.")
            duplicate = self._duplicate(q)
            if duplicate:
                raise BankError(f'An active question with the same subject and text already exists: {duplicate}.')
            self._insert(q)
        return self.get(q['id'])

    def update_question(self, question_id, changes, expected_revision):
        with self._write():
            old = self._current(question_id, expected_revision)
            if not old['active']:
                raise BankError('Restore this archived question before editing it.')
            q = deepcopy(old)
            for field in CONTENT_FIELDS:
                if field in changes:
                    q[field] = deepcopy(changes[field])
            for field in ('subject','unit','topic'):
                if isinstance(q.get(field),str): q[field] = q[field].strip()
            self._require_valid(q)
            duplicate = self._duplicate(q, question_id)
            if duplicate:
                raise BankError(f'An active question with the same subject and text already exists: {duplicate}.')
            if any(q[field] != old[field] for field in CONTENT_FIELDS):
                self.connection.execute('''UPDATE questions SET subject=?,unit=?,topic=?,kind=?,marks=?,
                    difficulty=?,prompt=?,answer=?,rubric=?,options_json=?,correct_option_id=?,prompt_hash=?,
                    review_status='draft',review_note='Content edited; review again before use.',
                    revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?''',
                    (q['subject'],q['unit'],q['topic'],q['kind'],q['marks'],q['difficulty'],q['prompt'],q['answer'],
                     q['rubric'],json.dumps(q['options'],ensure_ascii=False),q['correct_option_id'],prompt_hash(q['prompt']),question_id))
        return self.get(question_id)

    def approve_question(self, question_id, expected_revision, reviewer):
        if not isinstance(reviewer,str) or not reviewer.strip():
            raise BankError('Enter the name of the teacher reviewing this question.')
        with self._write():
            q = self._current(question_id, expected_revision)
            if not q['active']:
                raise BankError('Restore this question before approving it.')
            self._require_valid(q)
            note = 'Reviewed by ' + reviewer.strip()[:100] + ' on ' + datetime.now().strftime('%Y-%m-%d') + '.'
            if q['is_demo']:
                note += ' Demo origin retained; excluded from production eligibility.'
            self.connection.execute('''UPDATE questions SET review_status='approved',review_note=?,
                revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?''',(note,question_id))
        return self.get(question_id)

    def set_archived(self, question_id, archived, expected_revision):
        if type(archived) is not bool:
            raise BankError('Archive flag must be true or false.')
        with self._write():
            q = self._current(question_id,expected_revision)
            if q['active'] == (not archived):
                return q
            if not archived:
                duplicate = self._duplicate(q,question_id)
                if duplicate:
                    raise BankError(f'Cannot restore: active question {duplicate} has the same subject and text.')
                self.connection.execute('''UPDATE questions SET active=1,review_status='draft',
                    review_note='Restored; review again before use.',revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?''',(question_id,))
            else:
                self.connection.execute('''UPDATE questions SET active=0,revision=revision+1,
                    updated_at=CURRENT_TIMESTAMP WHERE id=?''',(question_id,))
        return self.get(question_id)

    def batch_errors(self, questions):
        """Recheck identities/content against current DB; never write during preview."""
        errors = {}
        ids = {row['id'] for row in self.connection.execute('SELECT id FROM questions')}
        prompts = {(row['subject'],row['prompt_hash']):row['id'] for row in
                   self.connection.execute('SELECT id,subject,prompt_hash FROM questions WHERE active=1')}
        for index, question in enumerate(questions):
            q = new_question(question)
            row_errors = question_errors(q)
            if not row_errors:
                if q['id'] in ids:
                    row_errors.append(f"ID {q['id']} already exists in the bank or this file.")
                key = (q['subject'],prompt_hash(q['prompt']))
                if key in prompts:
                    row_errors.append(f'Same subject/text as active question or earlier row {prompts[key]}.')
                ids.add(q['id']); prompts[key] = q['id']
            if row_errors: errors[index] = row_errors
        return errors

    def import_questions(self, questions):
        if not questions:
            raise BankError('There are no questions to import.')
        if len(questions) > 1000:
            raise BankError('Import at most 1,000 questions per file.')
        # Snapshot the exact preview, then revalidate while holding the writer lock.
        batch = [new_question(q) for q in questions]
        with self._write():
            errors = self.batch_errors(batch)
            if errors:
                detail = '\n'.join(f"Record {i+1}: {' '.join(es)}" for i,es in errors.items())
                raise BankError('Nothing imported. Fix the following or refresh the preview:\n' + detail)
            for q in batch:
                self._insert(q)
        return len(batch)

    def seed_demo(self):
        questions = json.loads((ROOT/'data'/'demo_questions.json').read_text(encoding='utf-8'))
        for q in questions:
            self._require_valid(q)
        added = 0
        with self._write():
            for q in questions:
                if self.connection.execute('SELECT 1 FROM questions WHERE id=?',(q['id'],)).fetchone():
                    continue
                # A user-created equivalent must never cause startup failure or be overwritten.
                if self._duplicate(q):
                    continue
                self._insert(q); added += 1
        return added


def demo_blueprint():
    return json.loads((ROOT/'data'/'demo_blueprint.json').read_text(encoding='utf-8'))
