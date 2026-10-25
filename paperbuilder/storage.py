"""Local SQLite storage and safe demo seeding."""
from pathlib import Path
import json
import os
import sqlite3
from .validation import question_errors, prompt_hash

ROOT = Path(__file__).resolve().parent.parent


def default_database_path():
    base = Path(os.environ['LOCALAPPDATA']) if os.environ.get('LOCALAPPDATA') else Path.home() / '.local' / 'share'
    return base / 'QuestionPaperBuilder' / 'demo_v1.sqlite3'


class Repository:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys = ON')
        version = self.connection.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1):
            self.connection.close()
            raise ValueError(f'Unsupported database version {version}; no changes made.')
        self.connection.executescript((ROOT / 'paperbuilder' / 'schema.sql').read_text(encoding='utf-8'))

    def close(self):
        self.connection.close()

    def seed_demo(self):
        questions = json.loads((ROOT / 'data' / 'demo_questions.json').read_text(encoding='utf-8'))
        for q in questions:
            errors = question_errors(q)
            if errors:
                raise ValueError(f"{q.get('id')}: {' '.join(errors)}")
        added = 0
        with self.connection:
            for q in questions:
                if self.connection.execute('SELECT 1 FROM questions WHERE id = ?', (q['id'],)).fetchone():
                    continue  # Never overwrite existing edits during startup.
                self.connection.execute('''INSERT INTO questions
                    (id,subject,unit,topic,kind,marks,difficulty,prompt,answer,rubric,
                     options_json,correct_option_id,review_status,review_note,is_demo,prompt_hash)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (q['id'],q['subject'],q['unit'],q['topic'],q['kind'],q['marks'],q['difficulty'],
                     q['prompt'],q['answer'],q['rubric'],json.dumps(q.get('options', [])),
                     q.get('correct_option_id'),q['review_status'],q['review_note'],int(q['is_demo']),prompt_hash(q['prompt'])))
                added += 1
        return added

    def questions(self):
        result = []
        for row in self.connection.execute('SELECT * FROM questions ORDER BY id'):
            q = dict(row)
            q['options'] = json.loads(q.pop('options_json'))
            q['is_demo'] = bool(q['is_demo']); q['active'] = bool(q['active'])
            result.append(q)
        return result


def demo_blueprint():
    return json.loads((ROOT / 'data' / 'demo_blueprint.json').read_text(encoding='utf-8'))
