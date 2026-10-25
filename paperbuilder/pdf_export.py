"""Printable A4 exports from validated snapshots, with explicit audience fields."""
from copy import deepcopy
from pathlib import Path
from xml.sax.saxutils import escape
import os
import textwrap
import unicodedata
from .file_output import staged_output
from .papers import validate_snapshot
from .validation import DIFFICULTIES


class ExportError(ValueError):
    pass


def export_blocks(paper, teacher=False):
    """Allowlist student fields; never serialize the whole snapshot into a PDF."""
    validate_snapshot(paper)
    if type(teacher) is not bool:
        raise ExportError('Choose student paper or teacher key.')
    bp = paper['blueprint']
    blocks = [('title', bp['title']), ('subject', bp['subject']),
              ('meta', f"Time: {bp['duration_minutes']} minutes | Total marks: {bp['total_marks']}"),
              ('instructions', bp.get('instructions', ''))]
    if teacher:
        blocks += [('meta', 'TEACHER ANSWER KEY - Contains answers'),
                   ('meta', 'Paper ID: ' + paper['paper_id']),
                   ('meta', f"Initial seed: {paper['seed']} | Replacements: {paper.get('replacement_count', 0)}")]
        if paper.get('parent_paper_id'):
            blocks.append(('meta', 'Revision of: ' + paper['parent_paper_id']))
    section = None
    for item in paper['items']:
        q = item['question']
        if item['section'] != section:
            section = item['section']; blocks.append(('section', 'Section ' + section))
        blocks += [('question', f"Question {item['number']}   [{q['marks']} marks]"),
                   ('pre' if '\n' in q['prompt'] else 'body', q['prompt'])]
        blocks += [('body', f"{option['id']}. {option['text']}") for option in q['options']]
        if teacher:
            blocks += [('meta', f"ID: {q['id']} | {q['unit']} | {q['difficulty']}"), ('label', 'Model answer')]
            if q.get('correct_option_id'):
                blocks.append(('body', 'Correct option: ' + q['correct_option_id']))
            blocks += [('code' if q['kind'] == 'Coding' or '\n' in q['answer'] else 'body', q['answer']),
                       ('label', 'Marking guidance'), ('body', q['rubric'])]
        blocks.append(('space', ''))
    if teacher:
        summary = paper['summary']
        blocks += [('section', 'Balance by marks'),
                   ('body', f"{summary['question_count']} questions | {summary['total_marks']} marks"),
                   ('body', ' | '.join(f"{d}: {summary['difficulty_marks'][d]}" for d in DIFFICULTIES)),
                   ('body', ' | '.join(f'{u}: {m}' for u, m in sorted(summary['unit_marks'].items()))),
                   ('meta', 'The seed describes initial generation. Saved snapshots preserve later replacements.')]
    return blocks


def _imports():
    try:
        import reportlab
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Preformatted, Spacer, KeepTogether
        return locals()
    except ImportError as exc:
        raise ExportError('PDF export needs ReportLab. In the project folder run: py -3.12 -m pip install -r requirements.txt') from exc


def _fonts(api, blocks):
    metrics, TTFont = api['pdfmetrics'], api['TTFont']
    windows = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    bundled = Path(api['reportlab'].__file__).parent / 'fonts'
    choices = {
        'body': [windows/'segoeui.ttf', Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'), bundled/'Vera.ttf'],
        'mono': [windows/'consola.ttf', Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')],
    }
    fonts = {}
    for role in ('body', 'mono'):
        text = ''.join(value for kind, value in blocks if (kind in ('pre', 'code')) == (role == 'mono'))
        required = {ord(c) for c in text if c not in '\n\r\t'}
        for path in choices[role]:
            if not path.is_file(): continue
            name = 'QPB-' + role + '-' + path.stem
            try:
                if name not in metrics.getRegisteredFontNames():
                    metrics.registerFont(TTFont(name, str(path)))
                if required <= set(metrics.getFont(name).face.charToGlyph):
                    fonts[role] = name; break
            except (OSError, ValueError):
                continue
        if role == 'mono' and role not in fonts and required <= set(range(32, 127)):
            fonts[role] = 'Courier'
        if role not in fonts:
            raise ExportError('A PDF font cannot display some characters. Use supported text or install DejaVu Sans and DejaVu Sans Mono. The paper has not been changed.')
    return fonts


def _check_text(blocks):
    for kind, text in blocks:
        for char in text:
            value = ord(char)
            # These scripts require shaping/bidi handling beyond this first exporter.
            if (unicodedata.bidirectional(char) in ('R', 'AL', 'AN') or 0x0900 <= value <= 0x0DFF
                    or (unicodedata.category(char).startswith('C') and char not in '\n\r\t')):
                raise ExportError(f'PDF export does not yet support character U+{value:04X} or its script. The saved paper is unchanged.')


def _markup(text):
    # Literal user text must never become ReportLab markup, images, links or file reads.
    lines = text.replace('\r\n', '\n').replace('\r', '\n').expandtabs(4).split('\n')
    result = []
    for line in lines:
        indent = len(line) - len(line.lstrip(' '))
        result.append('&#160;' * indent + escape(line[indent:]))
    return '<br/>'.join(result)


def _wrapped_code(text, width, continuation=False):
    lines = []
    for line in text.replace('\r\n', '\n').replace('\r', '\n').expandtabs(4).split('\n'):
        if not line:
            lines.append(''); continue
        wrapper = textwrap.TextWrapper(width=width, expand_tabs=False, replace_whitespace=False,
            drop_whitespace=False, break_long_words=True, break_on_hyphens=False,
            subsequent_indent='> ' if continuation else '')
        lines.extend(wrapper.wrap(line))
    return '\n'.join(lines)


def _build_pdf(paper, blocks, destination, teacher):
    api = _imports(); _check_text(blocks); fonts = _fonts(api, blocks)
    Style, Paragraph, Preformatted = api['ParagraphStyle'], api['Paragraph'], api['Preformatted']
    colors = api['colors']; A4 = api['A4']
    styles = {
        'title': Style('Title', fontName=fonts['body'], fontSize=19, leading=24, spaceAfter=8),
        'subject': Style('Subject', fontName=fonts['body'], fontSize=12, leading=16, spaceAfter=6),
        'body': Style('Body', fontName=fonts['body'], fontSize=10, leading=14, spaceAfter=5),
        'meta': Style('Meta', fontName=fonts['body'], fontSize=8.5, leading=12, spaceAfter=5, textColor=colors.HexColor('#344054')),
        'section': Style('Section', fontName=fonts['body'], fontSize=13, leading=17, spaceBefore=8, spaceAfter=7, keepWithNext=True),
        'question': Style('Question', fontName=fonts['body'], fontSize=10, leading=14, spaceAfter=4, keepWithNext=True),
        'label': Style('Label', fontName=fonts['body'], fontSize=9, leading=13, spaceBefore=4, spaceAfter=3, keepWithNext=True),
        'code': Style('Code', fontName=fonts['mono'], fontSize=9, leading=12, spaceAfter=7),
    }
    doc = api['SimpleDocTemplate'](str(destination), pagesize=A4,
        leftMargin=48, rightMargin=48, topMargin=58, bottomMargin=58,
        title=paper['blueprint']['title'], author='Question Paper Builder',
        subject='Teacher answer key' if teacher else 'Student question paper')
    body_width = A4[0] - 96 - 12  # Include Platypus frame padding.
    mono = api['pdfmetrics'].stringWidth('M', fonts['mono'], 9)
    line_width = max(20, int(body_width / mono) - 1)
    story = []
    question_group = []
    def flush_question():
        if question_group:
            story.append(api['KeepTogether'](question_group[:]))
            question_group.clear()
    for kind, text in blocks:
        if kind in ('question', 'section'): flush_question()
        if kind == 'space':
            (question_group if question_group else story).append(api['Spacer'](1, 8)); continue
        if not text: continue
        if kind in ('code', 'pre'):
            flowable = Preformatted(_wrapped_code(text, line_width, continuation=True), styles['code'], dedent=0)
        else:
            flowable = Paragraph(_markup(text), styles.get(kind, styles['body']))
        (question_group if kind == 'question' or question_group else story).append(flowable)
    flush_question()
    def page(canvas, document):
        canvas.saveState()
        canvas.setFont(fonts['body'], 8)
        canvas.setFillColor(colors.HexColor('#344054'))
        audience = 'TEACHER ANSWER KEY' if teacher else 'STUDENT QUESTION PAPER'
        canvas.drawString(48, A4[1]-32, audience)
        if paper['is_demo']:
            canvas.setFillColor(colors.HexColor('#922b21'))
            canvas.drawRightString(A4[0]-48, A4[1]-32, 'DEMONSTRATION ONLY - NOT AN APPROVED EXAM')
        canvas.setStrokeColor(colors.HexColor('#b7bdc6'))
        canvas.line(48, A4[1]-41, A4[0]-48, A4[1]-41)
        canvas.line(48, 44, A4[0]-48, 44)
        canvas.setFillColor(colors.HexColor('#344054'))
        canvas.setFont(fonts['body'], 7)
        canvas.drawString(48, 31, 'Long code lines wrap with > continuation; tabs display as four spaces.')
        canvas.drawRightString(A4[0]-48, 31, f'Page {document.page}')
        canvas.restoreState()
    doc.build(story, onFirstPage=page, onLaterPages=page)


def export_pdf(paper, destination, teacher=False, overwrite=False):
    snapshot = deepcopy(paper)
    try:
        blocks = export_blocks(snapshot, teacher)
        path = Path(destination).expanduser().resolve()
        if path.suffix.lower() != '.pdf':
            raise ExportError('Choose a filename ending in .pdf.')
        if path.exists() and overwrite:
            with path.open('rb') as stream:
                if stream.read(5) != b'%PDF-':
                    raise ExportError('Refusing to replace a file that is not a PDF. Choose a different filename.')
        with staged_output(path, overwrite=overwrite) as temporary:
            _build_pdf(snapshot, blocks, temporary, teacher)
        return path
    except Exception as exc:
        if isinstance(exc, ExportError): raise
        raise ExportError('PDF was not saved: ' + str(exc)) from exc
