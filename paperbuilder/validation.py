"""Pure validation rules. No Tkinter, SQL, or file writes."""
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import unicodedata

DIFFICULTIES = ('Easy', 'Medium', 'Hard')
KINDS = ('MCQ', 'Short answer', 'Coding')


def positive_int(value):
    return type(value) is int and value > 0


def prompt_hash(text):
    # Preserve internal whitespace, indentation and case because Python code is case-sensitive.
    normalized = unicodedata.normalize('NFC', text.replace('\r\n', '\n').replace('\r', '\n')).strip()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def question_errors(q):
    errors = []
    for field in ('id', 'subject', 'unit', 'prompt', 'answer', 'rubric'):
        if not isinstance(q.get(field), str) or not q[field].strip():
            errors.append(f'{field} is required.')
    if q.get('kind') not in KINDS:
        errors.append('Choose MCQ, Short answer or Coding.')
    if q.get('difficulty') not in DIFFICULTIES:
        errors.append('Choose Easy, Medium or Hard.')
    if not positive_int(q.get('marks')):
        errors.append('Marks must be a positive whole number.')
    status = q.get('review_status', 'draft')
    if status not in ('draft', 'demo_reviewed', 'approved'):
        errors.append('Invalid review status.')
    if type(q.get('is_demo', False)) is not bool:
        errors.append('is_demo must be true or false.')
    if status == 'demo_reviewed' and not q.get('is_demo'):
        errors.append('Demo review requires a demo question.')
    options = q.get('options', [])
    if not isinstance(options, list):
        errors.append('Options must be a list.')
        return errors
    if q.get('kind') == 'MCQ':
        if len(options) != 4 or any(not isinstance(o, dict) for o in options):
            errors.append('An MCQ needs four options.')
        else:
            ids = [o.get('id') for o in options]
            texts = [o.get('text') for o in options]
            valid_ids = all(isinstance(x, str) and x.strip() for x in ids)
            valid_texts = all(isinstance(x, str) and x.strip() for x in texts)
            if not valid_ids or len(set(ids)) != 4:
                errors.append('Option IDs must be nonempty and unique.')
            if not valid_texts or len(set(x.strip() for x in texts)) != 4:
                errors.append('Option text must be nonempty and distinct.')
            if q.get('correct_option_id') not in ids:
                errors.append('Correct option must identify an existing option.')
    elif options or q.get('correct_option_id'):
        errors.append('Only MCQs can have options or a correct option ID.')
    return errors


def selection_key(subject, row):
    return (subject, row['unit'], row['kind'], row['marks'], row['difficulty'])


def blueprint_errors(bp):
    errors = []
    for field in ('title', 'subject'):
        if not isinstance(bp.get(field), str) or not bp[field].strip():
            errors.append(f'{field} is required.')
    for field in ('total_marks', 'duration_minutes'):
        if not positive_int(bp.get(field)):
            errors.append(f'{field} must be a positive whole number.')
    targets = bp.get('difficulty_percent', {})
    percentages = {}
    if not isinstance(targets, dict) or set(targets) != set(DIFFICULTIES):
        errors.append('Supply exactly Easy, Medium and Hard percentage targets.')
    else:
        for level in DIFFICULTIES:
            try:
                number = Decimal(str(targets[level]))
                if not number.is_finite() or number < 0 or number > 100:
                    raise ValueError
                percentages[level] = number
            except (InvalidOperation, ValueError):
                errors.append(f'{level} percentage must be between 0 and 100.')
        if len(percentages) == 3 and sum(percentages.values()) != 100:
            errors.append('Difficulty percentages must total 100.')
    rows = bp.get('rows')
    if not isinstance(rows, list) or not rows:
        return errors + ['At least one blueprint row is required.']
    achieved = Counter()
    all_rows_valid = True
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            errors.append(f'Row {index} must be an object.'); all_rows_valid = False; continue
        valid = (all(isinstance(row.get(f), str) and row[f].strip() for f in ('section','unit'))
                 and row.get('kind') in KINDS and row.get('difficulty') in DIFFICULTIES
                 and positive_int(row.get('marks')) and positive_int(row.get('count')))
        if not valid:
            errors.append(f'Row {index}: provide section, unit, type, difficulty and positive integer marks/count.')
            all_rows_valid = False
            continue
        achieved[row['difficulty']] += row['marks'] * row['count']
    if all_rows_valid and positive_int(bp.get('total_marks')):
        if sum(achieved.values()) != bp['total_marks']:
            errors.append(f"Rows allocate {sum(achieved.values())} marks, but the paper requests {bp['total_marks']}.")
        if len(percentages) == 3:
            for level, percentage in percentages.items():
                target = Decimal(bp['total_marks']) * percentage / 100
                if target != target.to_integral_value():
                    errors.append(f'{level} target is {target} marks; choose an exact whole-mark target.')
                elif achieved[level] != target:
                    errors.append(f'{level}: rows allocate {achieved[level]} marks; target is {target}.')
    return errors


def availability(bp, questions, include_demo=False):
    """Aggregate repeated buckets; section is not part of candidate eligibility."""
    errors = blueprint_errors(bp)
    if errors:
        return {'valid': False, 'errors': errors, 'groups': []}
    demand = Counter()
    for row in bp['rows']:
        demand[selection_key(bp['subject'], row)] += row['count']
    supply = Counter()
    seen = set()
    for q in questions:
        if q['id'] in seen:
            continue
        seen.add(q['id'])
        if not q.get('active', True):
            continue
        if q.get('is_demo') and not include_demo:
            continue
        if q.get('review_status') == 'approved' or (
                include_demo and q.get('is_demo') and q.get('review_status') == 'demo_reviewed'):
            supply[selection_key(q['subject'], q)] += 1
    groups = []
    for key, required in demand.items():
        subject, unit, kind, marks, difficulty = key
        found = supply[key]
        groups.append(dict(subject=subject, unit=unit, kind=kind, marks=marks,
                           difficulty=difficulty, required=required, available=found,
                           shortage=max(0, required-found)))
    return {'valid': all(g['shortage'] == 0 for g in groups), 'errors': [], 'groups': groups}
