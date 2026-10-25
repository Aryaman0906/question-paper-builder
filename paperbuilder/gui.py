"""Phase 3 desktop app: editable blueprints and balanced generation."""
import tkinter as tk
import sqlite3
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from .validation import availability
from .question_bank import BankPanel
from .blueprint_gui import BlueprintPanel
from .generation import generate_paper, preview_text, GenerationError


class Application:
    def __init__(self, root, repository):
        self.root = root
        self.repo = repository
        self.paper = None
        root.title('Question Paper Builder | Blueprints and generation 0.3')
        root.geometry('1160x760'); root.minsize(850, 620)
        style = ttk.Style(root)
        if 'clam' in style.theme_names(): style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('TFrame', background='#f6f8fb')
        style.configure('TLabel', background='#f6f8fb', foreground='#172c43')
        style.configure('Heading.TLabel', font=('Segoe UI', 20, 'bold'))
        style.configure('TButton', padding=(12, 7))
        style.configure('Treeview', rowheight=28)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        wrapper = ttk.Frame(root, padding=18); wrapper.pack(fill='both', expand=True)
        ttk.Label(wrapper, text='Question Paper Builder', style='Heading.TLabel').pack(anchor='w')
        ttk.Label(wrapper, text='Question bank and paper generation • Phase 3').pack(anchor='w', pady=(4,10))
        self.notebook = ttk.Notebook(wrapper); self.notebook.pack(fill='both', expand=True)
        self.frames = {}
        for title in ('Home','Question bank','Paper setup','Availability','Review','Saved papers','Help'):
            frame = ttk.Frame(self.notebook, padding=14)
            self.notebook.add(frame, text=title); self.frames[title] = frame
        self.home(); self.bank(); self.setup(); self.availability_screen()
        self.review_screen()
        self.future('Saved papers', 'Saved paper history',
                    'Planned for 28–29 October: reopen exact snapshots. Editing a question in the bank must not change an existing paper.',
                    ('Open paper','Create revision','Export again'))
        self.help_screen()
        ttk.Label(wrapper, text='Demo samples need instructor review. Generated previews are temporary; saving papers and PDF export come next.').pack(anchor='w', pady=(10,0))
        root.bind('<Control-1>', lambda _: self.go('Home'))
        root.bind('<Control-2>', lambda _: self.go('Question bank'))
        root.bind('<Control-3>', lambda _: self.go('Paper setup'))
        root.protocol('WM_DELETE_WINDOW', self.close)

    def close(self):
        editor = self.bank_panel.editor
        if editor is not None and editor.winfo_exists():
            editor.cancel()
            if editor.winfo_exists():
                return
        row_editor = self.setup_panel.row_editor
        if row_editor is not None and row_editor.winfo_exists() and not row_editor.cancel():
            return
        if (self.setup_panel.dirty() or self.paper) and not messagebox.askyesno(
                'Close with unsaved work?', 'Unsaved blueprint edits and the generated preview will be lost. Close the app?', parent=self.root):
            return
        self.root.destroy()

    def go(self, title): self.notebook.select(self.frames[title])

    def label(self, frame, text):
        return ttk.Label(frame, text=text, wraplength=760, justify='left')

    def home(self):
        f = self.frames['Home']
        ttk.Label(f, text='Start with a clear paper blueprint', style='Heading.TLabel').pack(anchor='w', pady=(8,14))
        self.label(f, 'Manage and approve your questions, create an exact blueprint, then generate a paper and inspect its student preview and teacher key.').pack(anchor='w', pady=(0,20))
        for title, detail, target in (
            ('1  Manage your question bank','Add, edit, approve, archive or import questions.','Question bank'),
            ('2  Build the blueprint','Edit details, difficulty targets and ordered selection rows.','Paper setup'),
            ('3  Generate a paper','Check current availability, then select unique matching questions.','Availability')):
            box=ttk.LabelFrame(f, text=title, padding=14); box.pack(fill='x', pady=6)
            self.label(box,detail).pack(side='left')
            ttk.Button(box, text='Open', command=lambda t=target:self.go(t)).pack(side='right')
        self.label(f,'Blueprint templates and balanced generation are ready. Next: replacement, saved-paper history and export.').pack(anchor='w', pady=16)

    def bank(self):
        self.bank_panel = BankPanel(self.frames['Question bank'], self.repo, self.invalidate)

    def set_text(self, widget, text):
        widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',text);widget.configure(state='disabled')

    def setup(self):
        self.setup_panel = BlueprintPanel(self.frames['Paper setup'], self.repo, self.invalidate, self.check)

    def invalidate(self):
        self.paper = None
        if hasattr(self, 'generate_button'):
            self.generate_button.configure(state='disabled')
            self.set_text(self.result,'Setup or bank changed. Check availability again before generating.')
        if hasattr(self, 'student_text'):
            self.set_text(self.student_text,'No current paper. Generate from Availability.')
            self.set_text(self.teacher_text,'No current answer key.')
            self.balance.set('No generated paper. Changes to setup or bank invalidate the current preview.')

    def availability_screen(self):
        f=self.frames['Availability']
        self.label(f,'Production mode uses active, approved, non-demo questions. Opt into demo samples explicitly for practice. Generation rechecks the current bank every time.').pack(anchor='w',pady=(0,10))
        controls=ttk.Frame(f);controls.pack(fill='x',pady=(0,10))
        self.include_demo=tk.BooleanVar(value=False)
        ttk.Checkbutton(controls,text='Demo mode (allow sample questions)',variable=self.include_demo,command=self.invalidate).pack(side='left')
        ttk.Label(controls,text='Seed (optional)').pack(side='left',padx=(14,5))
        self.seed=tk.StringVar();ttk.Entry(controls,textvariable=self.seed,width=22).pack(side='left')
        self.seed.trace_add('write',lambda *_:self.invalidate())
        self.result=ScrolledText(f,height=16,wrap='word',font=('Consolas',11),state='disabled');self.result.pack(fill='both',expand=True)
        self.set_text(self.result,'Edit Paper setup, then check availability. The supplied example needs demo mode unless you add enough approved questions.')
        row=ttk.Frame(f);row.pack(fill='x',pady=12)
        ttk.Button(row,text='Check blueprint',command=self.check).pack(side='left')
        ttk.Button(row,text='Edit setup',command=lambda:self.go('Paper setup')).pack(side='left',padx=8)
        self.generate_button=ttk.Button(row,text='Generate paper',command=self.generate,state='disabled');self.generate_button.pack(side='left')
        self.label(f,'A seed repeats selection only with the same eligible bank, blueprint and generator/runtime. Blank chooses a fresh seed. Different seeds may still select the same questions.').pack(anchor='w')

    def check(self):
        try:
            report=availability(self.setup_panel.blueprint(),self.repo.questions(),include_demo=self.include_demo.get())
        except sqlite3.Error as exc:
            self.generate_button.configure(state='disabled')
            self.set_text(self.result,'Cannot read the bank: '+str(exc));self.go('Availability');return False
        lines=['READY TO GENERATE' if report['valid'] else 'CHANGES NEEDED','']+report['errors']
        for g in report['groups']:
            lines.append(f"{g['unit']} | {g['kind']} | {g['marks']} marks | {g['difficulty']}\nNeed {g['required']}; available {g['available']}; shortfall {g['shortage']}\n")
        self.generate_button.configure(state='normal' if report['valid'] else 'disabled')
        self.set_text(self.result,'\n'.join(lines));self.go('Availability')
        return report['valid']

    def generate(self):
        if self.paper and not messagebox.askyesno('Replace preview?','Generate again and replace the current unsaved preview?',parent=self.root):
            return
        raw=self.seed.get().strip()
        try:
            if raw and (not raw.isascii() or not raw.isdigit() or len(raw)>19):
                raise GenerationError('Enter a whole-number seed from 0 to 9223372036854775807, or leave it blank.')
            paper=generate_paper(self.setup_panel.blueprint(),self.repo.questions(),self.include_demo.get(),int(raw) if raw else None)
        except (GenerationError, sqlite3.Error) as exc:
            self.set_text(self.result,str(exc));self.generate_button.configure(state='disabled');self.go('Availability');return
        self.paper=paper
        self.set_text(self.student_text,preview_text(paper))
        self.set_text(self.teacher_text,preview_text(paper,teacher=True))
        summary=paper['summary'];bp=paper['blueprint']
        # Label marks and percentages explicitly; they are different quantities.
        details=' | '.join(f"{d}: {m} marks ({100*m/bp['total_marks']:g}%; target {bp['difficulty_percent'][d]}%)" for d,m in summary['difficulty_marks'].items())
        self.balance.set(('DEMO ONLY • ' if paper['is_demo'] else 'Approved bank • ')+
                         f"{summary['question_count']} unique questions • {summary['total_marks']} marks • Seed {paper['seed']}\n"+
                         details+'\nUnits: '+', '.join(f'{u}: {m} marks' for u,m in summary['unit_marks'].items()))
        self.preview_tabs.select(0);self.go('Review')

    def review_screen(self):
        f=self.frames['Review'];self.balance=tk.StringVar(value='No generated paper.')
        ttk.Label(f,textvariable=self.balance,wraplength=1000).pack(anchor='w',pady=(0,10))
        self.preview_tabs=ttk.Notebook(f);self.preview_tabs.pack(fill='both',expand=True)
        for name,attribute in (('Student paper','student_text'),('Teacher key','teacher_text')):
            frame=ttk.Frame(self.preview_tabs);self.preview_tabs.add(frame,text=name)
            box=ScrolledText(frame,wrap='word',font=('Consolas',11),state='disabled');box.pack(fill='both',expand=True)
            setattr(self,attribute,box);self.set_text(box,'Generate a paper from Availability.')
        self.label(f,'Temporary preview: closing the app or editing setup/bank clears it. Saving, replacement and PDF export arrive in later phases.').pack(anchor='w',pady=(8,0))

    def future(self,title,heading,body,buttons):
        f=self.frames[title];ttk.Label(f,text=heading,style='Heading.TLabel').pack(anchor='w',pady=12)
        self.label(f,body).pack(anchor='w',pady=10)
        self.label(f,'This screen is planned. Current generated previews are not saved to history.').pack(anchor='w',pady=10)
        for text in buttons:ttk.Button(f,text=text,state='disabled').pack(anchor='w',pady=5)

    def help_screen(self):
        f=self.frames['Help']
        text='''WHAT WORKS NOW
• Add, edit, search and filter your question bank.
• Approve questions with a review note; archive or restore.
• Preview CSV imports and save all valid records as drafts.
• Inspect model answers and rubrics.
• Add/edit/reorder blueprint rows and save/load templates.
• Check exact shortages; generate unique matching questions.
• Inspect separate student and teacher previews with balance totals.
• Reopen the app without duplicating or overwriting seeded questions.

WHAT COMES NEXT
28–29 Oct: compatible replacement and saved-paper history.
30–31 Oct: PDF export and backups.

DIFFICULTY
Easy / Medium / Hard are estimated labels for a target cohort.
Percentages refer to marks, not counts. No AI calibration is claimed.

KEYBOARD
Ctrl+1 Home, Ctrl+2 Question bank, Ctrl+3 Paper setup.
Use Tab / Shift+Tab to move through controls.

VERSION
0.3.0 — Blueprints and generation. Python standard library only.

REVIEW AND IMPORT
New/imported questions are drafts. Editing content resets approval.
Restore returns an archived question to draft. Demo origin is retained.
CSV: UTF-8, comma-separated, maximum 1,000 records / 2 MiB.
A file with any errors is not imported. No rows are overwritten.'''
        box=ScrolledText(f,wrap='word',font=('Segoe UI',11));box.pack(fill='both',expand=True);self.set_text(box,text)
