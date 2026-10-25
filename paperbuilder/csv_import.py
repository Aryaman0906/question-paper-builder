"""Strict, bounded UTF-8 CSV parsing, preview validation and templates."""
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
import csv
import re
from .storage import BankError
from .validation import question_errors

HEADERS = ('id','subject','unit','topic','kind','marks','difficulty','prompt','answer','rubric',
           'option_a','option_b','option_c','option_d','correct_option')
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000


@dataclass
class PreviewRow:
    line: int
    question: dict
    errors: list = field(default_factory=list)


@dataclass
class Preview:
    rows: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    skipped_blank: int = 0

    @property
    def ready(self):
        return bool(self.rows) and not self.errors and not any(r.errors for r in self.rows)

    @property
    def questions(self):
        return [r.question for r in self.rows]


def parse_csv(text):
    preview = Preview()
    if not isinstance(text,str):
        preview.errors.append('CSV must be UTF-8 text.'); return preview
    if '\x00' in text:
        preview.errors.append('The file contains NUL characters. Save it as UTF-8 CSV, not an Excel workbook.'); return preview
    if len(text.encode('utf-8')) > MAX_BYTES:
        preview.errors.append('Use a CSV smaller than 2 MiB.'); return preview
    reader = csv.DictReader(StringIO(text.lstrip('\ufeff'), newline=''), strict=True)
    try:
        headers = reader.fieldnames
        if not headers:
            preview.errors.append('The file is empty or has no header.'); return preview
        if len(headers) != len(set(headers)):
            preview.errors.append('The CSV contains duplicate column headers.'); return preview
        missing = set(HEADERS)-set(headers)
        unexpected = set(headers)-set(HEADERS)
        if missing or unexpected:
            if missing: preview.errors.append('Missing columns: ' + ', '.join(sorted(missing)))
            if unexpected: preview.errors.append('Unknown columns: ' + ', '.join(sorted(unexpected)))
            preview.errors.append('Use Save CSV template for the exact column names; comma-separated UTF-8 only.')
            return preview
        while True:
            try:
                row = next(reader)
            except StopIteration:
                break
            start_line = reader.line_num  # Physical end line, accurate for multiline cells.
            if None not in row and all(value is not None for value in row.values()) and not any(value.strip() for value in row.values()):
                preview.skipped_blank += 1; continue
            if len(preview.rows) >= MAX_ROWS:
                preview.errors.append("Import at most 1,000 nonempty records per file."); break
            if None in row or any(value is None for value in row.values()):
                preview.rows.append(PreviewRow(start_line,{},['Wrong number of columns. Quote commas and line breaks inside cells.']))
                continue
            q = {name:row[name] for name in ('id','subject','unit','topic','kind','difficulty','prompt','answer','rubric')}
            for name in ('id','subject','unit','topic','kind','difficulty'):
                q[name] = q[name].strip()
            raw_marks = row['marks'].strip()
            q['marks'] = int(raw_marks) if re.fullmatch(r'[0-9]{1,9}',raw_marks) else raw_marks
            q.update(review_status='draft',is_demo=False,active=True,review_note='Imported; awaiting teacher review.')
            options = [{'id':key,'text':row['option_'+key.lower()]} for key in 'ABCD']
            q['options'] = options if q['kind'] == 'MCQ' else []
            q['correct_option_id'] = row['correct_option'].strip().upper() or None
            errors = question_errors(q)
            if q['kind'] != 'MCQ' and any(o['text'].strip() for o in options):
                errors.append('Non-MCQ rows must leave all option columns blank.')
            preview.rows.append(PreviewRow(start_line,q,errors))
        if not preview.rows:
            preview.errors.append('No nonempty question records found.')
    except (csv.Error, ValueError) as exc:
        preview.errors.append(f'CSV format error near physical line {reader.line_num}: {exc}')
    return preview


def read_preview(path, repository):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        return Preview(errors=['Use a CSV smaller than 2 MiB.'])
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        return Preview(errors=['Could not decode UTF-8. Save as CSV UTF-8, not legacy ANSI or XLSX.'])
    preview = parse_csv(text)
    attach_bank_errors(preview, repository)
    return preview


def attach_bank_errors(preview, repository):
    candidates = [(i,r.question) for i,r in enumerate(preview.rows) if not r.errors]
    for position, errors in repository.batch_errors([q for _,q in candidates]).items():
        preview.rows[candidates[position][0]].errors.extend(errors)


def commit_preview(preview, repository):
    if not preview.ready:
        raise BankError('Nothing imported. Correct all errors and load the file again.')
    return repository.import_questions(preview.questions)


def template_text():
    out = StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(HEADERS)
    return out.getvalue()


def save_template(path):
    with Path(path).open('w',encoding='utf-8-sig',newline='') as stream:
        stream.write(template_text())
