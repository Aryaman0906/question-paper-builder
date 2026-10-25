"""Immutable paper snapshots, revision lineage and compatible replacement."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import re
import uuid
from . import __version__
from .generation import paper_errors
from .storage import BankError
from .validation import eligible, question_errors, selection_key


def _identifier(value):
    return isinstance(value, str) and re.fullmatch(r'P-[0-9a-f]{32}', value) is not None


def validate_snapshot(paper):
    """Validate both the selection and the persisted envelope; never consult live bank."""
    try:
        if not isinstance(paper, dict):
            raise ValueError('Paper must be a record.')
        if type(paper.get('schema_version')) is not int or paper['schema_version'] != 1:
            raise ValueError('Unsupported paper snapshot version.')
        if not _identifier(paper.get('paper_id')):
            raise ValueError('Invalid paper ID.')
        if not isinstance(paper.get('app_version'), str) or not paper['app_version'].strip():
            raise ValueError('Missing application version.')
        stamp = datetime.fromisoformat(paper['created_at'])
        if stamp.utcoffset() is None:
            raise ValueError('Paper creation time must include a timezone.')
        if type(paper.get('seed')) is not int or not 0 <= paper['seed'] < 2**63:
            raise ValueError('Invalid generation seed.')
        parent = paper.get('parent_paper_id')
        if parent is not None and (not _identifier(parent) or parent == paper['paper_id']):
            raise ValueError('Invalid revision parent.')
        count = paper.get('replacement_count', 0)
        if type(count) is not int or count < 0:
            raise ValueError('Invalid replacement count.')
        errors = paper_errors(paper)
        if errors:
            raise ValueError('\n'.join(errors))
        for item in paper['items']:
            q = item['question']
            if type(q.get('active')) is not bool or type(q.get('is_demo')) is not bool:
                raise ValueError('Question eligibility flags must be explicit booleans.')
            if 'options' not in q:
                raise ValueError('Question options are missing.')
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        raise BankError('Invalid paper snapshot: ' + str(exc)) from exc


def _encode(paper):
    validate_snapshot(paper)
    try:
        return json.dumps(paper, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError, RecursionError) as exc:
        raise BankError('Paper contains data that cannot be saved as JSON.') from exc


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field: ' + key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('Invalid JSON number: ' + value)


def load_paper(repository, identifier):
    row = repository.connection.execute('SELECT * FROM papers WHERE id=?', (identifier,)).fetchone()
    if row is None:
        raise BankError('This saved paper no longer exists. Refresh the history.')
    try:
        paper = json.loads(row['snapshot_json'], object_pairs_hook=_pairs, parse_constant=_reject_constant)
        validate_snapshot(paper)
        expected = (paper['paper_id'], paper['blueprint']['title'], paper['schema_version'],
                    paper['app_version'], int(paper['is_demo']), paper['created_at'])
        actual = tuple(row[k] for k in ('id', 'title', 'schema_version', 'app_version', 'is_demo', 'created_at'))
        if actual != expected:
            raise ValueError('Stored metadata does not match the snapshot.')
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        raise BankError('Cannot open saved paper: ' + str(exc)) from exc
    return paper


def list_papers(repository):
    return [dict(row) for row in repository.connection.execute('''SELECT id,title,is_demo,created_at
        FROM papers ORDER BY created_at DESC,rowid DESC''')]


def save_paper(repository, paper):
    """Atomic, retry-safe insert. An existing ID may never acquire different content."""
    snapshot = deepcopy(paper)
    encoded = _encode(snapshot)
    with repository._write():
        existing = repository.connection.execute('SELECT 1 FROM papers WHERE id=?', (snapshot['paper_id'],)).fetchone()
        if existing:
            if _encode(load_paper(repository, snapshot['paper_id'])) != encoded:
                raise BankError('This paper is already saved. Create a revision to make changes.')
            return snapshot['paper_id']
        parent_id = snapshot.get('parent_paper_id')
        if parent_id:
            parent = load_paper(repository, parent_id)
            if any(snapshot[k] != parent[k] for k in ('blueprint', 'is_demo', 'seed')):
                raise BankError('A replacement revision must preserve its parent blueprint, mode and seed.')
        repository.connection.execute('''INSERT INTO papers
            (id,title,schema_version,app_version,snapshot_json,is_demo,created_at) VALUES (?,?,?,?,?,?,?)''',
            (snapshot['paper_id'], snapshot['blueprint']['title'], snapshot['schema_version'],
             snapshot['app_version'], encoded, int(snapshot['is_demo']), snapshot['created_at']))
    return snapshot['paper_id']


def create_revision(repository, identifier):
    """Start an unsaved copy of a saved paper. No database write until Save paper."""
    paper = load_paper(repository, identifier)
    paper.update(parent_paper_id=identifier, paper_id='P-' + uuid.uuid4().hex,
                 created_at=datetime.now(timezone.utc).isoformat(), app_version=__version__)
    return paper


def replacement_candidates(paper, number, questions):
    validate_snapshot(paper)
    if type(number) is not int or not 1 <= number <= len(paper['items']):
        raise BankError('Select a question number from this paper.')
    old = paper['items'][number - 1]['question']
    used = {item['question']['id'] for item in paper['items']}
    key = selection_key(old['subject'], old)
    seen, result = {}, []
    for q in questions:
        if not isinstance(q, dict) or not isinstance(q.get('id'), str):
            raise BankError('The bank contains a malformed question.')
        if q['id'] in seen:
            if seen[q['id']] != q:
                raise BankError('Conflicting bank records share ID ' + q['id'] + '.')
            continue
        seen[q['id']] = q
        if q['id'] in used or not eligible(q, paper['is_demo']):
            continue
        if question_errors(q):
            continue
        if selection_key(q['subject'], q) == key:
            result.append(deepcopy(q))
    return sorted(result, key=lambda q: q['id'])


def replace_question(repository, paper, number, expected_candidate):
    """Recheck the exact previewed candidate against the current bank before applying."""
    validate_snapshot(paper)
    if repository.connection.execute('SELECT 1 FROM papers WHERE id=?', (paper['paper_id'],)).fetchone():
        raise BankError('Saved papers are read-only. Create a revision first.')
    candidates = replacement_candidates(paper, number, repository.questions())
    candidate = next((q for q in candidates if q == expected_candidate), None)
    if candidate is None:
        raise BankError('The replacement changed or is no longer available. Reopen the replacement list.')
    updated = deepcopy(paper)
    updated['items'][number - 1]['question'] = candidate
    updated['replacement_count'] = updated.get('replacement_count', 0) + 1
    validate_snapshot(updated)
    return updated
