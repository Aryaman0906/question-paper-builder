"""Navigable desktop wireframe. Later-stage actions are deliberately disabled."""
from copy import deepcopy
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from .storage import demo_blueprint
from .validation import availability


class Application:
    def __init__(self, root, repository):
        self.root = root
        self.repo = repository
        self.blueprint = demo_blueprint()
        root.title('Question Paper Builder | Foundation 0.1')
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
        ttk.Label(wrapper, text='Demo workspace • Foundation milestone • 22–23 October 2026').pack(anchor='w', pady=(4,10))
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

    def go(self, title): self.notebook.select(self.frames[title])

    def label(self, frame, text):
        return ttk.Label(frame, text=text, wraplength=760, justify='left')

    def home(self):
        f = self.frames['Home']
        ttk.Label(f, text='Start with a clear paper blueprint', style='Heading.TLabel').pack(anchor='w', pady=(8,14))
        self.label(f, 'This starter lets you inspect the demonstration bank, examine a 40-mark blueprint and check question availability. The remaining screens show the agreed workflow.').pack(anchor='w', pady=(0,20))
        for title, detail, target in (
            ('1  Inspect 40 sample questions','Read prompts, answers and marking guidance.','Question bank'),
            ('2  Examine the blueprint','Six selection groups, 13 questions, 40 marks.','Paper setup'),
            ('3  Check availability','See exactly which groups have sufficient questions.','Availability')):
            box=ttk.LabelFrame(f, text=title, padding=14); box.pack(fill='x', pady=6)
            self.label(box,detail).pack(side='left')
            ttk.Button(box, text='Open', command=lambda t=target:self.go(t)).pack(side='right')
        self.label(f,'Next milestone: question editing, approval, archiving and CSV import on 24–25 October.').pack(anchor='w', pady=16)

    def bank(self):
        f=self.frames['Question bank']
        bar=ttk.Frame(f);bar.pack(fill='x',pady=(0,10))
        ttk.Label(bar,text='Search questions').pack(side='left')
        self.query=tk.StringVar(); ttk.Entry(bar,textvariable=self.query,width=30).pack(side='left',padx=8)
        self.unit=tk.StringVar(value='All units')
        box=ttk.Combobox(bar,textvariable=self.unit,values=('All units','Module 1','Module 2'),state='readonly',width=16);box.pack(side='left')
        ttk.Button(bar,text='Filter',command=self.refresh_bank).pack(side='left',padx=8)
        self.query.trace_add('write',lambda *_:self.refresh_bank());box.bind('<<ComboboxSelected>>',lambda _:self.refresh_bank())
        tree_frame=ttk.Frame(f);tree_frame.pack(fill='both',expand=True)
        columns=('id','unit','kind','marks','difficulty','prompt')
        self.tree=ttk.Treeview(tree_frame,columns=columns,show='headings',height=7,selectmode='browse')
        for name,width in zip(columns,(80,90,105,55,80,420)):
            self.tree.heading(name,text=name.title());self.tree.column(name,width=width,minwidth=45,stretch=name=='prompt')
        scroll=ttk.Scrollbar(tree_frame,orient='vertical',command=self.tree.yview);self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.tree.bind('<<TreeviewSelect>>',self.show_question)
        ttk.Label(f,text='Question and teacher answer').pack(anchor='w',pady=(10,4))
        self.detail=ScrolledText(f,height=10,wrap='word',font=('Consolas',10),state='disabled');self.detail.pack(fill='both',expand=True)
        bar=ttk.Frame(f);bar.pack(fill='x',pady=(10,0))
        for name in ('Add question','Edit question','Approve','Archive','Import CSV'):
            ttk.Button(bar,text=name,state='disabled').pack(side='left',padx=(0,5))
        self.label(f,'Editing and import are scheduled for 24–25 October. Demo review status does not mean faculty approval.').pack(anchor='w',pady=(5,0))
        self.refresh_bank()

    def refresh_bank(self):
        if not hasattr(self,'tree'): return
        self.tree.delete(*self.tree.get_children())
        self.visible={}
        for q in self.repo.questions():
            if self.unit.get()!='All units' and q['unit']!=self.unit.get(): continue
            if self.query.get().casefold() not in (q['id']+' '+q['prompt']+' '+q['topic']).casefold(): continue
            self.visible[q['id']]=q
            self.tree.insert('', 'end', iid=q['id'], values=(q['id'],q['unit'],q['kind'],q['marks'],q['difficulty'],q['prompt'].replace('\n',' ')))
        if hasattr(self,'detail'): self.set_text(self.detail,'Select a question to read its prompt, answer and rubric.')

    def set_text(self, widget, text):
        widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',text);widget.configure(state='disabled')

    def show_question(self, _=None):
        selected=self.tree.selection()
        if not selected:return
        q=self.visible[selected[0]]
        options='\n'.join(f"{o['id']}. {o['text']}" for o in q['options'])
        text=f"{q['id']} | {q['unit']} | {q['difficulty']} | {q['marks']} marks\n\n{q['prompt']}\n{options}\n\nMODEL ANSWER\n{q['answer']}\n\nMARKING GUIDANCE\n{q['rubric']}\n\nREVIEW\n{q['review_note']}"
        self.set_text(self.detail,text)

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
        self.label(f,'The default check includes technically reviewed sample questions in this demo workspace. Production eligibility will require instructor-approved, non-demo questions.').pack(anchor='w',pady=(0,12))
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
        report=availability(bp,self.repo.questions(),include_demo=True)
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
• Browse and filter 40 demonstration questions.
• Inspect model answers and rubrics.
• Check the example blueprint and view shortages or validation errors.
• Reopen the app without duplicating or overwriting seeded questions.

WHAT COMES NEXT
24–25 Oct: editing, approval, archive and CSV import.
26–27 Oct: editable blueprints and generation.
28–31 Oct: review, history, PDF export and backups.

DIFFICULTY
Easy / Medium / Hard are estimated labels for a target cohort.
Percentages refer to marks, not counts. No AI calibration is claimed.

KEYBOARD
Ctrl+1 Home, Ctrl+2 Question bank, Ctrl+3 Paper setup.
Use Tab / Shift+Tab to move through controls.

VERSION
0.1.0 — Foundation milestone. Python standard library only.'''
        box=ScrolledText(f,wrap='word',font=('Segoe UI',11));box.pack(fill='both',expand=True);self.set_text(box,text)
