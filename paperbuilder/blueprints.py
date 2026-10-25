"""Validated, immutable saved blueprint copies using the existing schema."""
from copy import deepcopy
import json
import uuid
from .storage import BankError
from .validation import blueprint_errors


def save_blueprint(repository, blueprint):
    bp = deepcopy(blueprint)
    errors = blueprint_errors(bp)
    if errors:
        raise BankError('\n'.join(errors))
    # Save a new copy each time, avoiding accidental overwrite of another window.
    identifier = 'BP-' + uuid.uuid4().hex
    with repository._write():
        repository.connection.execute('''INSERT INTO blueprints
            (id,title,subject,duration_minutes,total_marks,instructions,targets_json)
            VALUES (?,?,?,?,?,?,?)''',
            (identifier, bp['title'], bp['subject'], bp['duration_minutes'], bp['total_marks'],
             bp.get('instructions', ''), json.dumps({d:str(v) for d,v in bp['difficulty_percent'].items()})))
        for position, row in enumerate(bp['rows'], 1):
            repository.connection.execute('''INSERT INTO blueprint_rows
                (blueprint_id,position,section,unit,kind,marks,difficulty,question_count)
                VALUES (?,?,?,?,?,?,?,?)''',
                (identifier,position,row['section'],row['unit'],row['kind'],row['marks'],row['difficulty'],row['count']))
    return identifier


def list_blueprints(repository):
    return [dict(r) for r in repository.connection.execute(
        'SELECT id,title,subject,total_marks,created_at FROM blueprints ORDER BY created_at DESC,rowid DESC')]


def load_blueprint(repository, identifier):
    # A single read transaction keeps the header and rows from different queries consistent.
    with repository.connection:
        repository.connection.execute('BEGIN')
        row = repository.connection.execute('SELECT * FROM blueprints WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise BankError('This saved blueprint no longer exists. Refresh the list.')
        bp = dict(row)
        bp.pop('created_at')
        try:
            bp['difficulty_percent'] = json.loads(bp.pop('targets_json'))
        except (ValueError, TypeError) as exc:
            raise BankError('Saved blueprint targets are unreadable.') from exc
        bp['rows'] = [dict(r) for r in repository.connection.execute('''SELECT section,unit,kind,marks,
            difficulty,question_count AS count FROM blueprint_rows WHERE blueprint_id=? ORDER BY position''', (identifier,))]
    errors = blueprint_errors(bp)
    if errors:
        raise BankError('Saved blueprint is invalid:\n' + '\n'.join(errors))
    return bp
