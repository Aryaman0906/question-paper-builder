"""Phase 2 desktop app: working question bank and blueprint availability."""
from copy import deepcopy
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from .storage import demo_blueprint
from .validation import availability
from .question_bank import BankPanel


class Application:
    def __init__(self, root, repository):
        self.root = root
        self.repo = repository
        self.blueprint = demo_blueprint()
        root.title('Question Paper Builder | Question bank 0.2')
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
        ttk.Label(wrapper, text='Local question bank • Phase 2 • New questions and demo samples').pack(anchor='w', pady=(4,10))
        self.notebook = ttk.Notebook(wrapper); self.notebook.pack(fill='both', expand=True)
        self.frames = {}
        for title in ('Home','Question bank','Paper setup','Availability','Review','Saved papers','Help'):
            frame = ttk.Frame(self.notebook, padding=14)
            self.notebook.add(frame, text=title); self.frames[title] = frame
        self.home(); self.bank(); self.setup(); self.availability_screen()
        self.future('Review', 'Review the paper before export',
                    'Planned for 28–31 October: a complete paper preview, compatible replacement, balance summary and separate answer-key preview.',
                    ('Replace question','Save paper','Export student PDF','Export answer key'))
        self.future('Saved papers', 'Saved paper history',
                    'Planned for 28–29 October: reopen exact snapshots. Editing a question in the bank must not change an existing paper.',
                    ('Open paper','Create revision','Export again'))
        self.help_screen()
        ttk.Label(wrapper, text='Sample content is technically checked, not instructor approved. No generation or PDF export in this milestone.').pack(anchor='w', pady=(10,0))
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
        self.root.destroy()

    def go(self, title): self.notebook.select(self.frames[title])

    def label(self, frame, text):
        return ttk.Label(frame, text=text, wraplength=760, justify='left')

    def home(self):
        f = self.frames['Home']
        ttk.Label(f, text='Start with a clear paper blueprint', style='Heading.TLabel').pack(anchor='w', pady=(8,14))
        self.label(f, 'Manage questions, review their answers, approve them and import a CSV. You can also check availability for the example blueprint.').pack(anchor='w', pady=(0,20))
        for title, detail, target in (
            ('1  Manage your question bank','Add, edit, approve, archive or import questions.','Question bank'),
            ('2  Examine the blueprint','Six selection groups, 13 questions, 40 marks.','Paper setup'),
            ('3  Check availability','See exactly which groups have sufficient questions.','Availability')):
            box=ttk.LabelFrame(f, text=title, padding=14); box.pack(fill='x', pady=6)
            self.label(box,detail).pack(side='left')
            ttk.Button(box, text='Open', command=lambda t=target:self.go(t)).pack(side='right')
        self.label(f,'Question-bank editing and CSV import are ready. Next milestone: editable blueprints and paper generation.').pack(anchor='w', pady=16)

    def bank(self):
        self.bank_panel = BankPanel(self.frames['Question bank'], self.repo)

    def set_text(self, widget, text):
        widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',text);widget.configure(state='disabled')

    def setup(self):
        f=self.frames['Paper setup']
        self.label(f,'Reference blueprint. You may change the total and difficulty targets to test validation; editing selection rows and saving templates are later milestones.').pack(anchor='w',pady=(0,12))
        fields=ttk.Frame(f);fields.pack(fill='x')
        self.inputs={}
        for index,(label,value) in enumerate((('Total marks','40'),('Minutes','60'),('Easy %','30'),('Medium %','50'),('Hard %','20'))):
            ttk.Label(fields,text=label).grid(row=0,column=index,sticky='w',padx=4)
            var=tk.StringVar(value=value);self.inputs[label]=var
            ttk.Entry(fields,textvariable=var,width=12).grid(row=1,column=index,sticky='w',padx=4,pady=6)
        cols=('section','unit','kind','difficulty','marks','count','subtotal')
        tree=ttk.Treeview(f,columns=cols,show='headings',height=7);tree.pack(fill='x',pady=16)
        for c in cols:tree.heading(c,text=c.title());tree.column(c,width=100,minwidth=60)
        for r in self.blueprint['rows']:tree.insert('','end',values=tuple(r[c] for c in cols[:-1])+(r['marks']*r['count'],))
        self.label(f,'Allocated: 40 marks · Easy 12 · Medium 20 · Hard 8\nUnit coverage: Module 1 = 18 marks; Module 2 = 22 marks. All questions compulsory.').pack(anchor='w')
        ttk.Button(f,text='Check availability',command=self.check).pack(anchor='w',pady=16)
        self.label(f,'Example check: change Total marks to 41, then check availability. You should see a validation message, not a silently changed paper.').pack(anchor='w')

    def availability_screen(self):
        f=self.frames['Availability']
        self.label(f,'This example check includes approved questions and technically reviewed demo samples. For a teacher-only check, uncheck Include demo samples.').pack(anchor='w',pady=(0,12))
        self.include_demo = tk.BooleanVar(value=True)
        ttk.Checkbutton(f,text='Include demo samples',variable=self.include_demo).pack(anchor='w',pady=(0,8))
        self.result=ScrolledText(f,height=18,wrap='word',font=('Consolas',11),state='disabled');self.result.pack(fill='both',expand=True)
        self.set_text(self.result,'Open Paper setup and choose Check availability.')
        row=ttk.Frame(f);row.pack(fill='x',pady=12)
        ttk.Button(row,text='Check blueprint',command=self.check).pack(side='left')
        ttk.Button(row,text='Edit setup',command=lambda:self.go('Paper setup')).pack(side='left',padx=8)
        ttk.Button(row,text='Generate paper',state='disabled').pack(side='left')
        self.label(f,'Generation is scheduled for 26–27 October. A successful availability check is not a generated paper.').pack(anchor='w')

    def check(self):
        bp=deepcopy(self.blueprint)
        try:
            bp['total_marks']=int(self.inputs['Total marks'].get())
            bp['duration_minutes']=int(self.inputs['Minutes'].get())
            bp['difficulty_percent']={d:self.inputs[d+' %'].get() for d in ('Easy','Medium','Hard')}
        except ValueError:
            self.set_text(self.result,'Please enter whole numbers for total marks and duration. Your entries have been preserved.')
            self.go('Availability');return
        report=availability(bp,self.repo.questions(),include_demo=self.include_demo.get())
        lines=['READY FOR LATER GENERATION' if report['valid'] else 'CHANGES NEEDED','']
        lines+=report['errors']
        for g in report['groups']:
            lines.append(f"{g['unit']} | {g['kind']} | {g['marks']} marks | {g['difficulty']}\nNeed {g['required']}; available {g['available']}; shortfall {g['shortage']}\n")
        self.set_text(self.result,'\n'.join(lines));self.go('Availability')

    def future(self,title,heading,body,buttons):
        f=self.frames[title];ttk.Label(f,text=heading,style='Heading.TLabel').pack(anchor='w',pady=12)
        self.label(f,body).pack(anchor='w',pady=10)
        self.label(f,'This is a screen sketch. No paper has been generated or saved.').pack(anchor='w',pady=10)
        for text in buttons:ttk.Button(f,text=text,state='disabled').pack(anchor='w',pady=5)

    def help_screen(self):
        f=self.frames['Help']
        text='''WHAT WORKS NOW
• Add, edit, search and filter your question bank.
• Approve questions with a review note; archive or restore.
• Preview CSV imports and save all valid records as drafts.
• Inspect model answers and rubrics.
• Check the example blueprint and view shortages or validation errors.
• Reopen the app without duplicating or overwriting seeded questions.

WHAT COMES NEXT
26–27 Oct: editable blueprints and generation.
28–31 Oct: review, history, PDF export and backups.

DIFFICULTY
Easy / Medium / Hard are estimated labels for a target cohort.
Percentages refer to marks, not counts. No AI calibration is claimed.

KEYBOARD
Ctrl+1 Home, Ctrl+2 Question bank, Ctrl+3 Paper setup.
Use Tab / Shift+Tab to move through controls.

VERSION
0.2.0 — Question-bank milestone. Python standard library only.

REVIEW AND IMPORT
New/imported questions are drafts. Editing content resets approval.
Restore returns an archived question to draft. Demo origin is retained.
CSV: UTF-8, comma-separated, maximum 1,000 records / 2 MiB.
A file with any errors is not imported. No rows are overwritten.'''
        box=ScrolledText(f,wrap='word',font=('Segoe UI',11));box.pack(fill='both',expand=True);self.set_text(box,text)
