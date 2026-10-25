"""Desktop workspace for question banks, blueprints and saved papers."""
import tkinter as tk
import sqlite3
from tkinter import ttk, messagebox, filedialog, font
from pathlib import Path
from .ui import ScrolledText, ScrollPage, setup_theme, decorate_text, NAV, BG
from .blueprints import list_blueprints
from .papers import list_papers
from . import __version__
from .validation import availability, DIFFICULTIES
from .question_bank import BankPanel
from .blueprint_gui import BlueprintPanel
from .generation import generate_paper, preview_text, GenerationError
from .papers import save_paper, load_paper, create_revision
from .paper_gui import HistoryPanel, ReplacementDialog
from .storage import BankError
from .pdf_export import export_pdf, ExportError
from .backup_gui import BackupDialog


class Application:
    def __init__(self, root, repository):
        self.root = root
        self.repo = repository
        self.paper = None
        self.paper_saved = False
        root.title('Question Paper Builder | Workspace ' + __version__)
        root.geometry('1280x850'); root.minsize(960, 680)
        self.font_family = setup_theme(root)
        shell = ttk.Frame(root); shell.pack(fill='both', expand=True)
        sidebar_width = max(204, font.Font(family=self.font_family,size=10,weight='bold').measure('04   Check & generate') + 64)
        sidebar = tk.Frame(shell, background=NAV, width=sidebar_width)
        sidebar.pack(side='left', fill='y'); sidebar.pack_propagate(False)
        self.sidebar_page = ScrollPage(sidebar)
        self.sidebar_page.pack(fill='both', expand=True)
        self.sidebar_page.canvas.configure(background=NAV)
        self.sidebar_page.body.configure(style='Nav.TFrame', padding=0)
        nav_content = self.sidebar_page.body
        tk.Label(nav_content, text='Q / P', font=(self.font_family, 23, 'bold'),
                 background=NAV, foreground='#B9ADFF').pack(anchor='w', padx=24, pady=(26, 4))
        tk.Label(nav_content, text='QUESTION PAPER\nBUILDER', justify='left',
                 font=(self.font_family, 10, 'bold'), background=NAV,
                 foreground='white').pack(anchor='w', padx=24)
        tk.Label(nav_content, text='YOUR WORKSPACE', font=(self.font_family, 8, 'bold'),
                 foreground='#929DB7', background=NAV).pack(anchor='w', padx=24, pady=(32, 10))
        self.nav_buttons = {}
        self.page_descriptions = {
            'Home': ('Workspace overview', 'A clear path from question bank to finished paper.'),
            'Question bank': ('Question bank', 'Curate questions, review answers and build a reliable bank.'),
            'Paper setup': ('Build your blueprint', 'Set the paper details, marks and question selection rules.'),
            'Availability': ('Check & generate', 'Check your question bank against the blueprint before generating.'),
            'Review': ('Paper studio', 'Review the paper, refine questions and export your final copies.'),
            'Saved papers': ('Saved papers', 'Return to an exact snapshot or start a new revision.'),
            'Help': ('Help & guidance', 'Everything you need to use your workspace confidently.')}
        names = ('Overview', 'Question bank', 'Paper setup', 'Check & generate', 'Paper studio', 'Saved papers', 'Help & guidance')
        for index, (title, label) in enumerate(zip(self.page_descriptions, names), 1):
            button = ttk.Button(nav_content, text=f'{index:02}   {label}', style='Nav.TButton',
                                command=lambda title=title: self.go(title))
            button.pack(fill='x', padx=10, pady=3); self.nav_buttons[title] = button
            root.bind(f'<Control-{index}>', lambda _, title=title: self.go(title))
        tk.Label(sidebar, text='LOCAL WORKSPACE\nYour work stays on this device.', justify='left',
                 font=(self.font_family, 8), foreground='#AAB4CC', background=NAV,
                 wraplength=sidebar_width-44).pack(side='bottom', anchor='w', padx=22, pady=18)
        ttk.Button(sidebar, text='Backup / restore', style='Nav.TButton',
                   command=lambda: BackupDialog(self.root, self.repo)).pack(side='bottom', fill='x', padx=10, pady=4)
        workspace = ttk.Frame(shell, padding=(24, 20, 10, 8)); workspace.pack(fill='both', expand=True)
        header = ttk.Frame(workspace); header.pack(fill='x', pady=(0, 14))
        self.page_title = tk.StringVar(value='Workspace overview')
        self.page_subtitle = tk.StringVar()
        ttk.Label(header, text='QUESTION PAPER BUILDER  /  WORKSPACE', style='Muted.TLabel').pack(anchor='w')
        title_row = ttk.Frame(header); title_row.pack(fill='x', pady=(6, 4))
        ttk.Label(title_row, textvariable=self.page_title, style='Heading.TLabel').pack(side='left')
        ttk.Label(header, textvariable=self.page_subtitle, style='Muted.TLabel', wraplength=700).pack(anchor='w')
        self.notebook = ttk.Notebook(workspace, style='Workspace.TNotebook')
        self.notebook.pack(fill='both', expand=True)
        self.frames = {}; self.pages = {}
        for title in self.page_descriptions:
            page = ScrollPage(self.notebook)
            self.notebook.add(page, text=title)
            self.pages[title] = page; self.frames[title] = page.body
        self.home(); self.bank(); self.setup(); self.availability_screen()
        self.review_screen()
        self.history = HistoryPanel(self.frames['Saved papers'], self.repo, self.open_saved)
        self.help_screen()
        self.notebook.bind('<<NotebookTabChanged>>', self.tab_changed)
        root.bind('<FocusIn>', self.focus_changed, add='+')
        ttk.Label(workspace, text='LOCAL WORKSPACE   •   v' + __version__,
                  style='Muted.TLabel').pack(anchor='w', pady=(8, 2))
        self.go('Home'); self.tab_changed()
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
        if (self.setup_panel.dirty() or (self.paper and not self.paper_saved)) and not messagebox.askyesno(
                'Close with unsaved work?', 'Unsaved blueprint edits and any unsaved paper will be lost. Saved copies remain in history. Close the app?', parent=self.root):
            return
        self.root.destroy()

    def go(self, title):
        self.notebook.select(self.pages[title])

    def focus_changed(self, event):
        self.sidebar_page.reveal(event.widget)
        for page in self.pages.values():
            if page.winfo_ismapped():
                page.reveal(event.widget)


    def label(self, frame, text):
        return ttk.Label(frame, text=text, wraplength=760, justify='left')

    def home(self):
        f = self.frames['Home']
        hero = tk.Frame(f, background='#EAE6FA', padx=24, pady=22)
        hero.pack(fill='x', pady=(0, 18))
        tk.Label(hero, text='THOUGHTFUL PAPERS. BALANCED ASSESSMENT.', background='#EAE6FA',
                 foreground='#6656A4', font=(self.font_family, 9, 'bold')).pack(anchor='w')
        tk.Label(hero, text='Your next paper starts here.', background='#EAE6FA',
                 foreground='#292344', justify='left', font=(self.font_family, 22, 'bold')).pack(anchor='w', pady=(8, 6))
        tk.Label(hero, text='Build a blueprint. Choose the right questions. Make every mark count.',
                 background='#EAE6FA', foreground='#5F5779', wraplength=740, justify='left').pack(anchor='w')
        ttk.Button(hero, text='Create a paper  →', style='Primary.TButton',
                   command=lambda: self.go('Paper setup')).pack(anchor='w', pady=(18, 0))
        stats = ttk.Frame(f); stats.pack(fill='x', pady=(0, 20))
        self.stat_values = {}; stat_cards = []; workflow_cards = []
        for column, (key, title, detail) in enumerate((
                ('questions', 'Active questions', 'Across your question bank'),
                ('approved', 'Ready for exams', 'Approved, non-demo questions'),
                ('templates', 'Blueprint templates', 'Saved paper structures'),
                ('papers', 'Saved papers', 'Includes paper revisions'))):
            stats.columnconfigure(column, weight=1, uniform='stats')
            card = ttk.Frame(stats, style='Card.TFrame', padding=(16, 14))
            stat_cards.append(card)
            card.grid(row=0, column=column, sticky='nsew', padx=(0, 10 if column < 3 else 0))
            var = tk.StringVar(value='—'); self.stat_values[key] = var
            ttk.Label(card, textvariable=var, style='Stat.TLabel').pack(anchor='w')
            ttk.Label(card, text=title, style='CardTitle.TLabel').pack(anchor='w', pady=(2, 5))
            ttk.Label(card, text=detail, style='CardMuted.TLabel', wraplength=165).pack(anchor='w')
        ttk.Label(f, text='A simple workflow', style='Section.TLabel').pack(anchor='w', pady=(0, 10))
        workflow = ttk.Frame(f); workflow.pack(fill='x')
        for column, (number, title, detail, target) in enumerate((
                ('01', 'Curate your bank', 'Add questions, check answers and approve content.', 'Question bank'),
                ('02', 'Shape your paper', 'Set marks, difficulty targets and ordered selection rows.', 'Paper setup'),
                ('03', 'Review & export', 'Check availability, generate and export separate PDFs.', 'Availability'))):
            workflow.columnconfigure(column, weight=1, uniform='steps')
            card = ttk.Frame(workflow, style='Card.TFrame', padding=18)
            workflow_cards.append(card)
            card.grid(row=0, column=column, sticky='nsew', padx=(0, 10 if column < 2 else 0))
            ttk.Label(card, text=number, style='Badge.TLabel').pack(anchor='w', pady=(0, 12))
            ttk.Label(card, text=title, style='CardTitle.TLabel').pack(anchor='w')
            ttk.Label(card, text=detail, style='CardMuted.TLabel', wraplength=220).pack(anchor='w', pady=(8, 14))
            ttk.Button(card, text='Open  →', command=lambda t=target: self.go(t)).pack(anchor='w', side='bottom')
        recent_header = ttk.Frame(f); recent_header.pack(fill='x', pady=(20, 8))
        ttk.Label(recent_header, text='Recently saved', style='Section.TLabel').pack(side='left')
        ttk.Button(recent_header, text='View history  →', command=lambda: self.go('Saved papers')).pack(side='right')
        self.recent_frame = ttk.Frame(f, style='Card.TFrame', padding=14)
        self.recent_frame.pack(fill='x')
        self.dashboard_note = tk.StringVar()
        note_label=ttk.Label(f, textvariable=self.dashboard_note, style='Muted.TLabel', wraplength=850)
        note_label.pack(anchor='w', pady=(12, 0))
        def reflow(event=None):
            width=event.width if event else self.pages['Home'].canvas.winfo_width()
            if width <= 1: return
            note_label.configure(wraplength=max(200,width-30))
            for row in self.recent_frame.winfo_children():
                labels=row.winfo_children() if isinstance(row,ttk.Frame) else [row]
                for label in labels:
                    if isinstance(label,ttk.Label):label.configure(wraplength=max(180,width-220))
            compact = width < 900
            stat_columns = (2 if width > font.nametofont('TkDefaultFont').measure('Blueprint templates') * 2 + 120 else 1) if compact else 4
            for label in hero.winfo_children():
                if isinstance(label,tk.Label): label.configure(wraplength=max(220,width-80))
            for frame, cards, columns in ((stats, stat_cards, stat_columns),
                                          (workflow, workflow_cards, 1 if compact else 3)):
                for column in range(len(cards)):
                    frame.columnconfigure(column, weight=1 if column < columns else 0,
                                          uniform='cards' if column < columns else '')
                for index, card in enumerate(cards):
                    for label in card.winfo_children():
                        if isinstance(label,ttk.Label): label.configure(wraplength=max(130,width//columns-60))
                    card.grid(row=index // columns, column=index % columns, sticky='nsew',
                              padx=(0, 10 if index % columns < columns - 1 else 0), pady=(0, 8 if compact else 0))
        self.home_reflow=reflow
        self.pages['Home'].canvas.bind('<Configure>', reflow, add='+')

    def refresh_home(self):
        try:
            questions = self.repo.questions()
            templates = list_blueprints(self.repo)
            papers = list_papers(self.repo)
        except sqlite3.Error as exc:
            for value in self.stat_values.values(): value.set('—')
            self.dashboard_note.set('Could not refresh the overview: ' + str(exc)); return
        counts = dict(questions=sum(q['active'] for q in questions),
                      approved=sum(q['active'] and q['review_status'] == 'approved' and not q['is_demo'] for q in questions),
                      templates=len(templates), papers=len(papers))
        for key, value in counts.items(): self.stat_values[key].set(str(value))
        for child in self.recent_frame.winfo_children(): child.destroy()
        if not papers:
            ttk.Label(self.recent_frame, text='No saved papers yet. Generate a paper, then choose Save paper in Paper studio.',
                      style='CardMuted.TLabel', wraplength=760).pack(anchor='w', pady=4)
        for paper in papers[:2]:
            row = ttk.Frame(self.recent_frame, style='Card.TFrame'); row.pack(fill='x', pady=4)
            ttk.Button(row, text='Open paper', command=lambda identifier=paper['id']: self.open_saved(identifier)).pack(side='right', padx=(16, 0))
            ttk.Label(row, text=paper['title'], style='CardTitle.TLabel', wraplength=580).pack(anchor='w')
            ttk.Label(row, text=('DEMO ONLY' if paper['is_demo'] else 'Production') + '  •  ' + paper['created_at'] + ' UTC',
                      style='CardMuted.TLabel').pack(anchor='w', pady=(3, 0))
        self.dashboard_note.set('Sample questions are for demonstration. Use reviewed, approved non-demo questions for real exams.')
        self.home_reflow()

    def bank(self):
        self.bank_panel = BankPanel(self.frames['Question bank'], self.repo, self.invalidate)

    def set_text(self, widget, text):
        widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',text);widget.configure(state='disabled')
        decorate_text(widget)

    def setup(self):
        self.setup_panel = BlueprintPanel(self.frames['Paper setup'], self.repo, self.invalidate, self.check)

    def invalidate(self):
        # Bank/setup edits invalidate availability, never an independent paper snapshot.
        if hasattr(self, 'generate_button'):
            self.generate_button.configure(state='disabled')
            self.set_text(self.result,'Setup or bank changed. Check availability again before generating. Any paper in Paper studio has been preserved with its own blueprint.')

    def discard_paper(self):
        return not (self.paper and not self.paper_saved) or messagebox.askyesno(
            'Replace unsaved paper?', 'This paper has not been saved. Discard it and open or generate another paper? Choose No to keep it and use Save paper first.', parent=self.root)

    def tab_changed(self, _event=None):
        selected = self.notebook.select()
        for title, page in self.pages.items():
            active = selected == str(page)
            self.nav_buttons[title].configure(style='Active.Nav.TButton' if active else 'Nav.TButton')
            if active:
                heading, detail = self.page_descriptions[title]
                self.page_title.set(heading); self.page_subtitle.set(detail)
                if title == 'Saved papers': self.history.refresh()
                if title == 'Home': self.refresh_home()

    def availability_screen(self):
        f=self.frames['Availability']
        self.label(f,'Production mode uses active, approved, non-demo questions. Enable demo mode to try the supplied samples. Your bank is checked again when generating.').pack(anchor='w',pady=(0,10))
        controls=ttk.Frame(f);controls.pack(fill='x',pady=(0,10))
        self.include_demo=tk.BooleanVar(value=False)
        ttk.Checkbutton(controls,text='Demo mode (allow sample questions)',variable=self.include_demo,command=self.invalidate).pack(side='left')
        ttk.Label(controls,text='Seed (optional)').pack(side='left',padx=(14,5))
        self.seed=tk.StringVar();ttk.Entry(controls,textvariable=self.seed,width=22).pack(side='left')
        self.seed.trace_add('write',lambda *_:self.invalidate())
        self.result=ScrolledText(f,height=13,wrap='word',font=('Consolas',11),state='disabled');self.result.pack(fill='both',expand=True)
        self.set_text(self.result,'READY WHEN YOU ARE\n\nChoose a blueprint in Paper setup, then select Check blueprint below.\n\nTrying the supplied sample? Enable Demo mode first. For a real exam, add and approve enough non-demo questions in your bank.')
        row=ttk.Frame(f);row.pack(fill='x',pady=12)
        ttk.Button(row,text='Check blueprint',command=self.check).pack(side='left')
        ttk.Button(row,text='Edit setup',command=lambda:self.go('Paper setup')).pack(side='left',padx=8)
        self.generate_button=ttk.Button(row,text='Generate paper',style='Primary.TButton',command=self.generate,state='disabled');self.generate_button.pack(side='left')
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
        if not self.discard_paper():
            return
        raw=self.seed.get().strip()
        try:
            if raw and (not raw.isascii() or not raw.isdigit() or len(raw)>19):
                raise GenerationError('Enter a whole-number seed from 0 to 9223372036854775807, or leave it blank.')
            paper=generate_paper(self.setup_panel.blueprint(),self.repo.questions(),self.include_demo.get(),int(raw) if raw else None)
        except (GenerationError, sqlite3.Error) as exc:
            self.set_text(self.result,str(exc));self.generate_button.configure(state='disabled');self.go('Availability');return
        self.show_paper(paper, saved=False)

    def show_paper(self, paper, saved):
        self.paper=paper
        self.paper_saved=saved
        self.set_text(self.student_text,preview_text(paper))
        self.set_text(self.teacher_text,preview_text(paper,teacher=True))
        summary=paper['summary'];bp=paper['blueprint']
        # Label marks and percentages explicitly; they are different quantities.
        details=' | '.join(f"{d}: {m} marks ({100*m/bp['total_marks']:g}%; target {bp['difficulty_percent'][d]}%)" for d in DIFFICULTIES for m in [summary['difficulty_marks'][d]])
        self.balance.set(('DEMO ONLY • ' if paper['is_demo'] else 'Approved bank • ')+
                         f"{summary['question_count']} unique questions • {summary['total_marks']} marks • Seed {paper['seed']}\n"+
                         details+'\nUnits: '+', '.join(f'{u}: {m} marks' for u,m in sorted(summary['unit_marks'].items())))
        self.paper_status.set(('Saved • read-only' if saved else 'UNSAVED • use Save paper') + ' | ' + paper['paper_id'] +
                              ('\nRevision of: ' + paper['parent_paper_id'] if paper.get('parent_paper_id') else '') +
                              f" | Replacements: {paper.get('replacement_count', 0)}")
        self.question_combo.configure(values=[str(i['number']) for i in paper['items']])
        self.question_number.set('1')
        self.save_button.configure(state='disabled' if saved else 'normal')
        self.replace_button.configure(state='disabled' if saved else 'normal')
        self.revision_button.configure(state='normal' if saved else 'disabled')
        self.student_pdf_button.configure(state='normal')
        self.teacher_pdf_button.configure(state='normal')
        self.preview_tabs.select(0);self.go('Review')

    def review_screen(self):
        f=self.frames['Review'];self.balance=tk.StringVar(value='No generated paper.')
        ttk.Label(f,textvariable=self.balance,wraplength=1000).pack(anchor='w',pady=(0,10))
        self.paper_status=tk.StringVar(value='No paper selected.')
        ttk.Label(f,textvariable=self.paper_status,wraplength=1000).pack(anchor='w',pady=(0,6))
        controls=ttk.Frame(f);controls.pack(fill='x',pady=(0,8))
        self.save_button=ttk.Button(controls,text='Save paper',style='Primary.TButton',command=self.save_current,state='disabled');self.save_button.pack(side='left')
        self.revision_button=ttk.Button(controls,text='Create revision',command=self.revise_current,state='disabled');self.revision_button.pack(side='left',padx=6)
        ttk.Label(controls,text='Question no.').pack(side='left',padx=(12,4))
        self.question_number=tk.StringVar()
        self.question_combo=ttk.Combobox(controls,textvariable=self.question_number,width=6,state='readonly');self.question_combo.pack(side='left')
        self.replace_button=ttk.Button(controls,text='Replace question',command=self.replace_current,state='disabled');self.replace_button.pack(side='left',padx=6)
        exports=ttk.Frame(f);exports.pack(fill='x',pady=(0,8))
        self.student_pdf_button=ttk.Button(exports,text='Export student PDF',command=lambda:self.export_current(False),state='disabled');self.student_pdf_button.pack(side='left')
        self.teacher_pdf_button=ttk.Button(exports,text='Export teacher key PDF',command=lambda:self.export_current(True),state='disabled');self.teacher_pdf_button.pack(side='left',padx=6)
        self.preview_tabs=ttk.Notebook(f);self.preview_tabs.pack(fill='both',expand=True)
        for name,attribute in (('Student paper','student_text'),('Teacher key','teacher_text')):
            frame=ttk.Frame(self.preview_tabs);self.preview_tabs.add(frame,text=name)
            box=ScrolledText(frame,height=12,wrap='word',font=('Consolas',11),state='disabled');box.pack(fill='both',expand=True)
            setattr(self,attribute,box);self.set_text(box,'Your paper preview will appear here.\n\n1. Set up a blueprint in Paper setup.\n2. Open Check & generate and check availability.\n3. Generate a paper, then return here to review and save it.')
        self.label(f,'Review uses its own blueprint and question snapshots. Bank/setup edits do not change this paper. Save before closing; saved copies require a new revision to edit.').pack(anchor='w',pady=(8,0))

    def export_current(self, teacher):
        if not self.paper:
            return
        kind='Teacher_Key' if teacher else 'Student_Paper'
        path=filedialog.asksaveasfilename(parent=self.root,title='Export '+kind.replace('_',' '),
            defaultextension='.pdf',filetypes=[('PDF document','*.pdf')],
            initialfile=kind+'_'+self.paper['paper_id']+'.pdf',confirmoverwrite=False)
        if not path:
            return
        destination=Path(path).expanduser().resolve()
        if destination == self.repo.path.resolve():
            messagebox.showerror('Cannot export','Choose a different file from the active database.',parent=self.root);return
        overwrite=destination.exists()
        if overwrite and not messagebox.askyesno('Replace existing PDF?',
                'Replace this file?\n'+str(destination),parent=self.root):
            return
        try:
            export_pdf(self.paper,destination,teacher=teacher,overwrite=overwrite)
        except ExportError as exc:
            messagebox.showerror('Cannot export PDF',str(exc),parent=self.root);return
        note='\nThis working paper is still unsaved in history. Use Save paper to retain it.' if not self.paper_saved else ''
        messagebox.showinfo('PDF exported',str(destination)+note,parent=self.root)

    def save_current(self):
        if not self.paper or self.paper_saved:
            return
        try:
            identifier=save_paper(self.repo,self.paper)
        except (BankError, sqlite3.Error) as exc:
            messagebox.showerror('Cannot save paper',str(exc),parent=self.root);return
        self.show_paper(self.paper,saved=True)
        self.history.refresh(identifier)

    def open_saved(self, identifier, revision=False):
        try:
            paper=create_revision(self.repo,identifier) if revision else load_paper(self.repo,identifier)
            # Build both previews before replacing any unsaved working copy.
            preview_text(paper);preview_text(paper,teacher=True)
        except (BankError, GenerationError, sqlite3.Error) as exc:
            messagebox.showerror('Cannot open paper',str(exc),parent=self.root);return
        if self.discard_paper():
            self.show_paper(paper,saved=not revision)

    def revise_current(self):
        if self.paper and self.paper_saved:
            self.open_saved(self.paper['paper_id'],revision=True)

    def replace_current(self):
        if not self.paper or self.paper_saved:
            return
        try:
            ReplacementDialog(self.root,self.repo,self.paper,int(self.question_number.get()),
                              lambda paper:self.show_paper(paper,saved=False))
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror('Cannot replace question',str(exc),parent=self.root)

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
• Replace a question with an unused eligible match; marks and balance stay exact.
• Save/reopen exact paper snapshots, even after bank edits or archives.
• Create and save revisions without overwriting their parent papers.
• Export separate printable A4 student and teacher PDFs.
• Back up all saved data and restore a validated backup with a recovery copy.

WHAT COMES NEXT
Windows scaling checks, observed user testing and the submission report.

DIFFICULTY
Easy / Medium / Hard are estimated labels for a target cohort.
Percentages refer to marks, not counts. No AI calibration is claimed.

KEYBOARD
Ctrl+1 Overview, Ctrl+2 Question bank, Ctrl+3 Paper setup.\nCtrl+4 Check & generate, Ctrl+5 Paper studio, Ctrl+6 Saved papers, Ctrl+7 Help.
Use Tab / Shift+Tab to move through controls.

VERSION
0.6.0 — Redesigned desktop workspace. ReportLab is needed only for PDF export.

SAVED PAPERS
Save paper stores the blueprint, ordered questions, answers and marking guidance.
Saved papers are read-only. Create revision makes an unsaved copy with a parent ID.
Save the revision to retain it. The original stays unchanged.
Replacements use the current bank; existing snapshot content is historical.
The seed describes initial generation, not replacements. Reopen exact saved copies.
Changing the setup or bank preserves the paper in Paper studio; generating another paper asks before discarding unsaved work.

PDF EXPORT AND BACKUPS
Export the open paper from Paper studio; history entries can be reopened and exported again.
Install PDF support once: py -3.12 -m pip install -r requirements.txt
Exports preserve code indentation. Long code lines use > continuation; tabs display as four spaces.
Fonts must cover the text. Complex scripts (including Hindi/Arabic) are not supported by this exporter yet.
Backup includes saved questions/templates/papers and teacher answers, not unsaved edits or exported PDFs.
Restore replaces data, creates a recovery backup, and closes the app. Reopen to refresh every screen.
Use a new backup filename each time; existing backup files are never overwritten.

REVIEW AND IMPORT
New/imported questions are drafts. Editing content resets approval.
Restore returns an archived question to draft. Demo origin is retained.
CSV: UTF-8, comma-separated, maximum 1,000 records / 2 MiB.
A file with any errors is not imported. No rows are overwritten.'''
        box=ScrolledText(f,height=18,wrap='word',font=('Segoe UI',11));box.pack(fill='both',expand=True);self.set_text(box,text)
