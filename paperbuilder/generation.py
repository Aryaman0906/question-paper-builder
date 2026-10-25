"""Exact fixed-group sampling, independent validation and text previews."""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import random
import secrets
import uuid
from . import __version__
from .validation import availability, blueprint_errors, eligible, question_errors, selection_key, DIFFICULTIES


class GenerationError(ValueError):
    pass


def paper_errors(paper):
    """Recompute constraints from actual selected records, not generator counters."""
    if not isinstance(paper, dict):
        return ['Paper must be a record.']
    bp = paper.get('blueprint')
    errors = blueprint_errors(bp)
    if errors:
        return errors
    if type(paper.get('is_demo')) is not bool:
        return ['Paper mode is missing or invalid.']
    items = paper.get('items')
    if not isinstance(items, list):
        return ['Selected questions must be a list.']
    counts, marks, units = Counter(), Counter(), Counter()
    seen = set()
    for position, item in enumerate(items, 1):
        if not isinstance(item, dict) or not isinstance(item.get('question'), dict):
            errors.append(f'Question {position} is not a record.'); continue
        q = item['question']
        q_errors = question_errors(q)
        if q_errors:
            errors.append(f'Question {position}: ' + ' '.join(q_errors)); continue
        if q['id'] in seen:
            errors.append(f'Duplicate question ID: {q["id"]}.')
        seen.add(q['id'])
        if type(item.get('number')) is not int or item.get('number') != position:
            errors.append('Question numbering must be consecutive.')
        index = item.get('row_index')
        if type(index) is not int or not 0 <= index < len(bp['rows']):
            errors.append(f'Question {position} has an invalid blueprint row.'); continue
        row = bp['rows'][index]
        if selection_key(q['subject'], q) != selection_key(bp['subject'], row) or item.get('section') != row['section']:
            errors.append(f'Question {position} does not match its blueprint row.')
        if not eligible(q, paper['is_demo']):
            errors.append(f'Question {q["id"]} is not eligible for this paper mode.')
        counts[index] += 1
        marks[q['difficulty']] += q['marks']
        units[q['unit']] += q['marks']
    expected_order = [i for i, row in enumerate(bp['rows']) for _ in range(row['count'])]
    if [item.get('row_index') if isinstance(item, dict) else None for item in items] != expected_order:
        errors.append('Selected questions must follow the blueprint row order.')
    for i, row in enumerate(bp['rows']):
        if counts[i] != row['count']:
            errors.append(f'Row {i+1}: selected {counts[i]}, expected {row["count"]}.')
    if sum(marks.values()) != bp['total_marks']:
        errors.append('Selected marks do not equal the requested total.')
    for level in DIFFICULTIES:
        target = Decimal(str(bp['difficulty_percent'][level])) * bp['total_marks'] / 100
        if marks[level] != target:
            errors.append(f'{level}: selected {marks[level]} marks, expected {target}.')
    expected_summary = dict(total_marks=sum(marks.values()), question_count=len(items),
                            difficulty_marks={d:marks[d] for d in DIFFICULTIES}, unit_marks=dict(units))
    if paper.get('summary') != expected_summary:
        errors.append('Balance summary does not match the selected questions.')
    return errors


def generate_paper(blueprint, questions, include_demo=False, seed=None):
    if type(include_demo) is not bool:
        raise GenerationError('Choose a valid demo or production mode.')
    if seed is not None and (type(seed) is not int or not 0 <= seed < 2**63):
        raise GenerationError('Seed must be a whole number from 0 to 9223372036854775807, or blank.')
    bp = deepcopy(blueprint)
    errors = blueprint_errors(bp)
    if errors:
        raise GenerationError('\n'.join(errors))
    bank = deepcopy(list(questions))
    seen, candidates = {}, []
    relevant = {selection_key(bp['subject'], r) for r in bp['rows']}
    for q in bank:
        if not isinstance(q, dict) or not isinstance(q.get('id'), str):
            raise GenerationError('The question bank contains a malformed record.')
        if q['id'] in seen:
            if q != seen[q['id']]:
                raise GenerationError('Conflicting bank records share ID ' + q['id'] + '.')
            continue
        seen[q['id']] = q
        if eligible(q, include_demo):
            errors = question_errors(q)
            if errors:
                raise GenerationError(f'Question {q["id"]} needs correction: ' + ' '.join(errors))
            if selection_key(q['subject'], q) in relevant:
                candidates.append(q)
    report = availability(bp, candidates, include_demo)
    if not report['valid']:
        shortages = [f'{g["unit"]} / {g["kind"]} / {g["difficulty"]} / {g["marks"]} marks: '
                     f'need {g["required"]}, available {g["available"]}, add {g["shortage"]}.'
                     for g in report['groups'] if g['shortage']]
        raise GenerationError('Cannot generate this blueprint.\n' + '\n'.join(shortages))
    actual_seed = secrets.randbits(63) if seed is None else seed
    rng = random.Random(actual_seed)
    pools, demands = defaultdict(list), Counter()
    for q in sorted(candidates, key=lambda q:q['id']):
        pools[selection_key(q['subject'], q)].append(q)
    for row in bp['rows']:
        demands[selection_key(bp['subject'], row)] += row['count']
    selected = {key:iter(rng.sample(pools[key], demands[key])) for key in sorted(demands)}
    items, marks, units = [], Counter(), Counter()
    for index, row in enumerate(bp['rows']):
        key = selection_key(bp['subject'], row)
        for _ in range(row['count']):
            q = next(selected[key])
            items.append(dict(number=len(items)+1, row_index=index, section=row['section'], question=q))
            marks[q['difficulty']] += q['marks']; units[q['unit']] += q['marks']
    paper = dict(schema_version=1, paper_id='P-'+uuid.uuid4().hex, app_version=__version__,
                 created_at=datetime.now(timezone.utc).isoformat(), seed=actual_seed,
                 is_demo=include_demo, blueprint=bp, items=items,
                 summary=dict(total_marks=sum(marks.values()), question_count=len(items),
                              difficulty_marks={d:marks[d] for d in DIFFICULTIES}, unit_marks=dict(units)))
    errors = paper_errors(paper)
    if errors:
        raise GenerationError('Generated paper failed validation:\n' + '\n'.join(errors))
    return paper


def preview_text(paper, teacher=False):
    errors = paper_errors(paper)
    if errors:
        raise GenerationError('Invalid paper: ' + '\n'.join(errors))
    bp = paper['blueprint']
    lines = (['DEMONSTRATION ONLY — NOT AN APPROVED EXAM', ''] if paper['is_demo'] else [])
    lines += [bp['title'], bp['subject'], f'Time: {bp["duration_minutes"]} minutes | Marks: {bp["total_marks"]}',
              bp.get('instructions',''), '']
    if teacher:
        lines += ['TEACHER ANSWER KEY', f'Generation seed: {paper["seed"]} (before any replacements)', f'Replacements: {paper.get("replacement_count", 0)}', '']
    last_section = None
    for item in paper['items']:
        q = item['question']
        if item['section'] != last_section:
            lines += ['Section ' + item['section'], '']; last_section = item['section']
        lines.append(f'{item["number"]}. {q["prompt"]} [{q["marks"]} marks]')
        lines += [f'   {o["id"]}. {o["text"]}' for o in q['options']]
        if teacher:
            lines += [f'ID: {q["id"]} | {q["unit"]} | {q["difficulty"]}',
                      'Correct option: '+q['correct_option_id'] if q.get('correct_option_id') else '',
                      'Answer: '+q['answer'], 'Marking guidance: '+q['rubric']]
        lines.append('')
    if teacher:
        summary = paper['summary']
        lines += ['BALANCE BY MARKS',
                  f"Total: {summary['total_marks']} marks | Questions: {summary['question_count']}",
                  ' | '.join(f"{d}: {summary['difficulty_marks'][d]} marks" for d in DIFFICULTIES),
                  ' | '.join(f"{u}: {m} marks" for u, m in sorted(summary['unit_marks'].items()))]
    return '\n'.join(lines)
