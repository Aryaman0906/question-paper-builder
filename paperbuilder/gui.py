"""Phase 5 desktop app: paper/key PDFs and database backup/restore."""
import tkinter as tk
import sqlite3
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from tkinter.scrolledtext import ScrolledText
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
        root.title('Question Paper Builder | PDF export and backups 0.5')
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
        heading=ttk.Frame(wrapper);heading.pack(fill='x')
        ttk.Label(heading, text='Question Paper Builder', style='Heading.TLabel').pack(side='left')
        ttk.Button(heading,text='Backup / restore',command=lambda:BackupDialog(self.root,self.repo)).pack(side='right')
        ttk.Label(wrapper, text='Question bank and paper generation • Phase 5').pack(anchor='w', pady=(4,10))
        self.notebook = ttk.Notebook(wrapper); self.notebook.pack(fill='both', expand=True)
        self.frames = {}
        for title in ('Home','Question bank','Paper setup','Availability','Review','Saved papers','Help'):
            frame = ttk.Frame(self.notebook, padding=14)
            self.notebook.add(frame, text=title); self.frames[title] = frame
        self.home(); self.bank(); self.setup(); self.availability_screen()
        self.review_screen()
        self.history = HistoryPanel(self.frames['Saved papers'], self.repo, self.open_saved)
        self.notebook.bind('<<NotebookTabChanged>>', self.tab_changed)
        self.help_screen()
        ttk.Label(wrapper, text='Demo samples need instructor review. Student and teacher PDFs are separate. Back up your saved data regularly.').pack(anchor='w', pady=(10,0))
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
        if (self.setup_panel.dirty() or (self.paper and not self.paper_saved)) and not messagebox.askyesno(
                'Close with unsaved work?', 'Unsaved blueprint edits and any unsaved paper will be lost. Saved copies remain in history. Close the app?', parent=self.root):
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
        self.label(f,'Generate, replace compatible questions, and save exact papers. Reopen saved papers or create revisions from history. Export student and teacher PDFs from Review. Use Backup / restore to protect saved data.').pack(anchor='w', pady=16)

    def bank(self):
        self.bank_panel = BankPanel(self.frames['Question bank'], self.repo, self.invalidate)

    def set_text(self, widget, text):
        widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',text);widget.configure(state='disabled')

    def setup(self):
        self.setup_panel = BlueprintPanel(self.frames['Paper setup'], self.repo, self.invalidate, self.check)

    def invalidate(self):
        # Bank/setup edits invalidate availability, never an independent paper snapshot.
        if hasattr(self, 'generate_button'):
            self.generate_button.configure(state='disabled')
            self.set_text(self.result,'Setup or bank changed. Check availability again before generating. Any paper in Review has been preserved with its own blueprint.')

    def discard_paper(self):
        return not (self.paper and not self.paper_saved) or messagebox.askyesno(
            'Replace unsaved paper?', 'This paper has not been saved. Discard it and open or generate another paper? Choose No to keep it and use Save paper first.', parent=self.root)

    def tab_changed(self, _event):
        if self.notebook.select() == str(self.frames['Saved papers']):
            self.history.refresh()

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
        self.save_button=ttk.Button(controls,text='Save paper',command=self.save_current,state='disabled');self.save_button.pack(side='left')
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
            box=ScrolledText(frame,wrap='word',font=('Consolas',11),state='disabled');box.pack(fill='both',expand=True)
            setattr(self,attribute,box);self.set_text(box,'Generate a paper from Availability.')
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
Final Windows acceptance, user testing, visual polish and submission report.

DIFFICULTY
Easy / Medium / Hard are estimated labels for a target cohort.
Percentages refer to marks, not counts. No AI calibration is claimed.

KEYBOARD
Ctrl+1 Home, Ctrl+2 Question bank, Ctrl+3 Paper setup.
Use Tab / Shift+Tab to move through controls.

VERSION
0.5.0 — PDF export and backups. ReportLab is needed only for PDF export.

SAVED PAPERS
Save paper stores the blueprint, ordered questions, answers and marking guidance.
Saved papers are read-only. Create revision makes an unsaved copy with a parent ID.
Save the revision to retain it. The original stays unchanged.
Replacements use the current bank; existing snapshot content is historical.
The seed describes initial generation, not replacements. Reopen exact saved copies.
Changing the setup or bank preserves Review; generating another paper asks before discarding unsaved work.

PDF EXPORT AND BACKUPS
Export the open paper from Review; history entries can be reopened and exported again.
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
        box=ScrolledText(f,wrap='word',font=('Segoe UI',11));box.pack(fill='both',expand=True);self.set_text(box,text)
