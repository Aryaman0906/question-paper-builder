"""Question editing, review and CSV import screens."""
from copy import deepcopy
from pathlib import Path
import sqlite3
import uuid
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from tkinter.scrolledtext import ScrolledText
from .storage import BankError
from .validation import KINDS, DIFFICULTIES
from .csv_import import read_preview, commit_preview, save_template


def display_text(widget, text):
    widget.configure(state='normal')
    widget.delete('1.0','end')
    widget.insert('1.0',text)
    widget.configure(state='disabled')


class QuestionEditor(tk.Toplevel):
    def __init__(self, parent, repository, on_saved, question=None):
        super().__init__(parent)
        self.repo = repository
        self.on_saved = on_saved
        self.question = deepcopy(question)
        self.title('Edit question' if question else 'Add question')
        self.geometry('790x650'); self.minsize(650,540)
        self.transient(parent.winfo_toplevel())
        self.protocol('WM_DELETE_WINDOW',self.cancel)
        self.bind('<Escape>',lambda _:self.cancel())
        body = ttk.Frame(self,padding=15);body.pack(fill='both',expand=True)
        body.columnconfigure(0,weight=1);body.rowconfigure(1,weight=1)
        ttk.Label(body,text='Save complete question content as a draft. Any content change requires review again.',wraplength=730).grid(row=0,column=0,sticky='w',pady=(0,10))
        self.tabs = ttk.Notebook(body);self.tabs.grid(row=1,column=0,sticky='nsew')
        metadata=ttk.Frame(self.tabs,padding=15)
        content=ttk.Frame(self.tabs,padding=12)
        options=ttk.Frame(self.tabs,padding=15)
        self.tabs.add(metadata,text='Details'); self.tabs.add(content,text='Question and answer'); self.tabs.add(options,text='MCQ options')
        self.vars = {};self.widgets={}
        defaults = dict(id='Q-'+uuid.uuid4().hex[:12],subject='Python Programming',unit='',topic='',kind='Short answer',marks='2',difficulty='Easy')
        if question:
            defaults.update(question)
        metadata.columnconfigure(1,weight=1)
        for row, (field,label) in enumerate((('id','Question ID'),('subject','Subject'),('unit','Unit / module'),('topic','Topic (optional)'),('kind','Question type'),('marks','Marks'),('difficulty','Difficulty'))):
            ttk.Label(metadata,text=label).grid(row=row,column=0,sticky='w',padx=(0,15),pady=8)
            self.vars[field]=tk.StringVar(value=str(defaults[field]))
            if field in ('kind','difficulty'):
                values = KINDS if field=='kind' else DIFFICULTIES
                w=ttk.Combobox(metadata,textvariable=self.vars[field],values=values,state='readonly')
            else:
                w=ttk.Entry(metadata,textvariable=self.vars[field])
                if field=='id' and question:w.configure(state='readonly')
            w.grid(row=row,column=1,sticky='ew',pady=8)
            self.widgets[field]=w
        ttk.Label(metadata,text='Difficulty is a teacher estimate. Marks must be a positive whole number.\nNew records are kept separate from demonstration questions.',wraplength=570).grid(row=7,column=0,columnspan=2,sticky='w',pady=12)
        self.texts={}
        for field,label,height in (('prompt','Question text',5),('answer','Model answer / explanation',6),('rubric','Marking guidance',3)):
            ttk.Label(content,text=label).pack(anchor='w',pady=(5,3))
            widget=ScrolledText(content,height=height,wrap='word',font=('Consolas',10),undo=True)
            widget.pack(fill='both',expand=True)
            widget.insert('1.0',defaults.get(field,''));self.texts[field]=widget
        self.option_texts=[]
        ttk.Label(options,text='For MCQs: enter four distinct options and choose the correct option.\nFor other types, option data is not stored.',wraplength=650).pack(anchor='w',pady=(0,10))
        by_id={o['id']:o['text'] for o in defaults.get('options',[])}
        for key in 'ABCD':
            ttk.Label(options,text='Option '+key).pack(anchor='w')
            w=ScrolledText(options,height=2,wrap='word',font=('Consolas',10),undo=True)
            w.pack(fill='x',pady=(0,8));w.insert('1.0',by_id.get(key,''));self.option_texts.append(w)
        self.correct=tk.StringVar(value=defaults.get('correct_option_id') or '')
        ttk.Label(options,text='Correct option').pack(anchor='w')
        self.correct_combo=ttk.Combobox(options,textvariable=self.correct,values=tuple('ABCD'),state='readonly',width=8)
        self.correct_combo.pack(anchor='w',pady=(3,0))
        self.kind_changed()
        self.widgets['kind'].bind('<<ComboboxSelected>>',lambda _:self.kind_changed())
        self.error=tk.StringVar()
        ttk.Label(body,textvariable=self.error,foreground='#9b2d20',wraplength=720).grid(row=2,column=0,sticky='ew',pady=(10,4))
        controls=ttk.Frame(body);controls.grid(row=3,column=0,sticky='ew')
        ttk.Button(controls,text='Save question',command=self.save).pack(side='right')
        ttk.Button(controls,text='Cancel',command=self.cancel).pack(side='right',padx=8)
        self.original = self.raw_state()
        self.grab_set();self.widgets['subject'].focus_set()

    def kind_changed(self):
        enabled=self.vars['kind'].get()=='MCQ'
        for w in self.option_texts:w.configure(state='normal' if enabled else 'disabled')
        self.correct_combo.configure(state='readonly' if enabled else 'disabled')

    def raw_state(self):
        return (tuple(v.get() for v in self.vars.values()),
                tuple(w.get('1.0','end-1c') for w in self.texts.values()),
                tuple(w.get('1.0','end-1c') for w in self.option_texts),self.correct.get())

    def form_question(self):
        q={k:v.get() for k,v in self.vars.items()}
        value=q['marks'].strip()
        q['marks']=int(value) if value.isascii() and value.isdigit() and len(value)<=9 else value
        q.update({field:w.get('1.0','end-1c') for field,w in self.texts.items()})
        q['options']=[];q['correct_option_id']=None
        if q['kind']=='MCQ':
            q['options']=[{'id':key,'text':w.get('1.0','end-1c')} for key,w in zip('ABCD',self.option_texts)]
            q['correct_option_id']=self.correct.get() or None
        return q

    def save(self):
        q=self.form_question()
        try:
            if self.question:
                saved=self.repo.update_question(self.question['id'],q,self.question['revision'])
            else:
                saved=self.repo.create_question(q)
        except BankError as exc:
            lines=str(exc).splitlines()
            self.error.set('\n'.join(lines[:3]) + ('\nCorrect these fields, then save again.' if len(lines)>3 else ''))
            # Show the tab containing the first invalid field, while preserving all entries.
            first=lines[0].lower() if lines else ''
            if any(word in first for word in ('prompt','answer','rubric')):
                self.tabs.select(1)
                field=next((x for x in self.texts if x in first),'prompt');self.texts[field].focus_set()
            elif any(word in first for word in ('option','mcq')):
                self.tabs.select(2)
            else:
                self.tabs.select(0)
            return
        self.on_saved(saved['id'],'Saved '+saved['id']+'. Status: '+saved['review_status'].replace('_',' ')+'.')
        self.destroy()

    def cancel(self):
        if self.raw_state()!=self.original and not messagebox.askyesno('Discard changes?','Discard the unsaved changes to this question?',parent=self):
            return
        self.destroy()


class ImportDialog(tk.Toplevel):
    def __init__(self,parent,repository,path,on_imported):
        super().__init__(parent)
        self.repo=repository;self.path=Path(path);self.on_imported=on_imported;self.preview=None
        self.title('Preview CSV import');self.geometry('1000x650');self.minsize(760,520)
        self.transient(parent.winfo_toplevel())
        self.bind('<Escape>',lambda _:self.destroy())
        body=ttk.Frame(self,padding=15);body.pack(fill='both',expand=True)
        self.filename=tk.StringVar(value=self.path.name)
        ttk.Label(body,textvariable=self.filename).pack(anchor='w')
        ttk.Label(body,text='Every row must pass. The exact preview will be imported as drafts; existing records are never overwritten.',wraplength=900).pack(anchor='w',pady=(5,8))
        self.summary=tk.StringVar();ttk.Label(body,textvariable=self.summary,wraplength=900).pack(anchor='w',pady=5)
        frame=ttk.Frame(body);frame.pack(fill='both',expand=True)
        cols=('line','id','status','prompt','errors')
        self.tree=ttk.Treeview(frame,columns=cols,show='headings',height=10,selectmode='browse')
        for name,label,width in zip(cols,('End line','ID','Status','Question','Errors'),(65,140,75,300,300)):
            self.tree.heading(name,text=label);self.tree.column(name,width=width,minwidth=50)
        scrollbar=ttk.Scrollbar(frame,orient='vertical',command=self.tree.yview)
        horizontal=ttk.Scrollbar(frame,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar.set,xscrollcommand=horizontal.set)
        self.tree.grid(row=0,column=0,sticky='nsew');scrollbar.grid(row=0,column=1,sticky='ns');horizontal.grid(row=1,column=0,sticky='ew')
        frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        self.tree.bind('<<TreeviewSelect>>',self.show_row)
        self.detail=ScrolledText(body,height=8,wrap='word',font=('Consolas',10),state='disabled');self.detail.pack(fill='both',expand=True,pady=10)
        buttons=ttk.Frame(body);buttons.pack(fill='x')
        ttk.Button(buttons,text='Reload file',command=self.reload).pack(side='left')
        self.commit_button=ttk.Button(buttons,text='Import all as drafts',command=self.commit,state='disabled');self.commit_button.pack(side='right')
        ttk.Button(buttons,text='Cancel',command=self.destroy).pack(side='right',padx=8)
        self.grab_set();self.reload()

    def reload(self):
        self.tree.delete(*self.tree.get_children());self.commit_button.configure(state='disabled');self.preview=None
        try:
            self.preview=read_preview(self.path,self.repo)
        except (OSError,sqlite3.Error) as exc:
            self.summary.set('Could not load the file. Nothing has been imported.')
            display_text(self.detail,str(exc));return
        p=self.preview
        invalid=sum(bool(r.errors) for r in p.rows)
        self.summary.set(f'{len(p.rows)} records: {len(p.rows)-invalid} ready, {invalid} with errors. No database changes yet.')
        for i,r in enumerate(p.rows):
            self.tree.insert('','end',iid=str(i),values=(r.line,r.question.get('id',''), 'Error' if r.errors else 'Ready',r.question.get('prompt','').replace('\n',' '),' '.join(r.errors)))
        display_text(self.detail,'\n'.join(p.errors) if p.errors else 'Select a row for its complete preview. End line is the physical CSV line where that record ends; multiline cells can span several lines.')
        if p.ready:self.commit_button.configure(state='normal')

    def show_row(self,_=None):
        if not self.tree.selection() or not self.preview:return
        r=self.preview.rows[int(self.tree.selection()[0])];q=r.question
        text=f"CSV record ending on line {r.line}\n"+'\n'.join(r.errors)+'\n\n'
        for field in ('id','subject','unit','topic','kind','marks','difficulty','prompt','answer','rubric'):
            text+=f"{field.upper()}\n{q.get(field,'')}\n\n"
        for option in q.get('options',[]):text+=f"Option {option['id']}: {option['text']}\n"
        if q.get('correct_option_id'):text+='Correct option: '+q['correct_option_id']
        if self.preview.errors:text+='\n\nFILE ERRORS\n'+'\n'.join(self.preview.errors)
        display_text(self.detail,text)

    def commit(self):
        if not self.preview or not self.preview.ready:return
        if not messagebox.askyesno('Import questions?',f'Import all {len(self.preview.rows)} previewed questions as drafts?',parent=self):return
        self.commit_button.configure(state='disabled');self.update_idletasks()
        try:
            count=commit_preview(self.preview,self.repo)
        except BankError as exc:
            self.summary.set('Nothing imported. Reload the file to refresh validation.')
            display_text(self.detail,str(exc));return
        self.on_imported(None,f'Imported {count} questions as drafts. Review them before approval.')
        self.destroy()


class BankPanel(ttk.Frame):
    def __init__(self,parent,repository):
        super().__init__(parent);self.pack(fill='both',expand=True)
        self.repo=repository;self.visible={};self.editor=None
        top=ttk.Frame(self);top.pack(fill='x')
        ttk.Label(top,text='Search').pack(side='left')
        self.query=tk.StringVar();search=ttk.Entry(top,textvariable=self.query,width=34);search.pack(side='left',padx=8)
        ttk.Button(top,text='Clear filters',command=self.clear_filters).pack(side='left')
        ttk.Button(top,text='Refresh',command=self.refresh).pack(side='left',padx=8)
        filters=ttk.Frame(self);filters.pack(fill='x',pady=(8,10))
        self.filters={};self.combos={}
        specifications=(('subject','Subject',('All subjects',)),('unit','Unit',('All units',)),
                        ('review','Review',('All reviews','Draft','Approved','Demo reviewed')),
                        ('active','Show',('Active','Archived','All records')))
        for key,label,values in specifications:
            ttk.Label(filters,text=label).pack(side='left',padx=(0,4))
            var=tk.StringVar(value=values[0]);self.filters[key]=var
            combo=ttk.Combobox(filters,textvariable=var,values=values,state='readonly',width=16 if key=='subject' else 13)
            combo.pack(side='left',padx=(0,10));self.combos[key]=combo
            combo.bind('<<ComboboxSelected>>',lambda _:self.refresh())
        self.query.trace_add('write',lambda *_:self.refresh())
        table=ttk.Frame(self);table.pack(fill='both',expand=True)
        cols=('id','subject','unit','kind','marks','difficulty','review','prompt')
        self.tree=ttk.Treeview(table,columns=cols,show='headings',selectmode='browse',height=7)
        for key,width in zip(cols,(145,140,95,110,55,80,115,360)):
            self.tree.heading(key,text=key.title());self.tree.column(key,width=width,minwidth=45,stretch=key=='prompt')
        y=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview);x=ttk.Scrollbar(table,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        self.tree.grid(row=0,column=0,sticky='nsew');y.grid(row=0,column=1,sticky='ns');x.grid(row=1,column=0,sticky='ew')
        table.rowconfigure(0,weight=1);table.columnconfigure(0,weight=1)
        self.tree.bind('<<TreeviewSelect>>',self.show_question);self.tree.bind('<Double-1>',lambda _:self.edit())
        self.count=tk.StringVar();ttk.Label(self,textvariable=self.count).pack(anchor='w',pady=4)
        self.detail=ScrolledText(self,height=8,wrap='word',font=('Consolas',10),state='disabled');self.detail.pack(fill='both',expand=True)
        controls=ttk.Frame(self);controls.pack(fill='x',pady=(10,4))
        ttk.Button(controls,text='Add question',command=self.add).pack(side='left',padx=(0,5))
        self.edit_button=ttk.Button(controls,text='Edit',command=self.edit,state='disabled');self.edit_button.pack(side='left',padx=(0,5))
        self.approve_button=ttk.Button(controls,text='Approve',command=self.approve,state='disabled');self.approve_button.pack(side='left',padx=(0,5))
        self.archive_button=ttk.Button(controls,text='Archive',command=self.archive,state='disabled');self.archive_button.pack(side='left',padx=(0,5))
        ttk.Button(controls,text='Import CSV',command=self.import_csv).pack(side='left',padx=(0,5))
        ttk.Button(controls,text='Save CSV template',command=self.template).pack(side='left')
        self.status=tk.StringVar(value='New and imported questions start as drafts. Content edits require review again.')
        ttk.Label(self,textvariable=self.status,wraplength=1000).pack(anchor='w')
        self.refresh()

    def clear_filters(self):
        for key,value in (('subject','All subjects'),('unit','All units'),('review','All reviews'),('active','Active')):
            self.filters[key].set(value)
        self.query.set('');self.refresh()

    def refresh(self,select=None,message=None):
        if not hasattr(self,'tree'):return
        previous=self.tree.selection()
        select=select or (previous[0] if previous else None)
        questions=self.repo.questions()
        self.combos['subject'].configure(values=('All subjects',)+tuple(sorted({q['subject'] for q in questions})))
        self.combos['unit'].configure(values=('All units',)+tuple(sorted({q['unit'] for q in questions})))
        self.tree.delete(*self.tree.get_children());self.visible={}
        reviews={'Draft':'draft','Approved':'approved','Demo reviewed':'demo_reviewed'}
        for q in questions:
            if self.filters['subject'].get()!='All subjects' and q['subject']!=self.filters['subject'].get():continue
            if self.filters['unit'].get()!='All units' and q['unit']!=self.filters['unit'].get():continue
            if self.filters['review'].get() in reviews and q['review_status']!=reviews[self.filters['review'].get()]:continue
            state=self.filters['active'].get()
            if state=='Active' and not q['active'] or state=='Archived' and q['active']:continue
            haystack=' '.join(str(q[field]) for field in ('id','subject','unit','topic','prompt')).casefold()
            if self.query.get().casefold() not in haystack:continue
            self.visible[q['id']]=q
            review=q['review_status'].replace('_',' ')+(' · demo' if q['is_demo'] else '')
            self.tree.insert('','end',iid=q['id'],values=(q['id'],q['subject'],q['unit'],q['kind'],q['marks'],q['difficulty'],review,q['prompt'].replace('\n',' ')))
        self.count.set(f'{len(self.visible)} shown · {sum(q["active"] for q in questions)} active · {sum(not q["active"] for q in questions)} archived')
        for button in (self.edit_button,self.approve_button,self.archive_button):button.configure(state='disabled')
        display_text(self.detail,'Select a question to read its prompt, model answer, marking guidance and review status.')
        if select in self.visible:
            self.tree.selection_set(select);self.tree.see(select);self.show_question()
        if message:
            self.status.set(message+(' Clear filters to see it.' if select and select not in self.visible else ''))

    def selected(self):
        selection=self.tree.selection()
        return self.repo.get(selection[0]) if selection else None

    def show_question(self,_=None):
        q=self.selected()
        if not q:return
        options='\n'.join(f"{o['id']}. {o['text']}" for o in q['options'])
        review=q['review_status'].replace('_',' ')+(' · DEMO ORIGIN' if q['is_demo'] else '')
        text=f"{q['id']} | {q['unit']} | {q['difficulty']} | {q['marks']} marks\nStatus: {review} | {'Active' if q['active'] else 'Archived'}\n\n{q['prompt']}\n{options}\n\nMODEL ANSWER\n{q['answer']}\n\nMARKING GUIDANCE\n{q['rubric']}\n\nREVIEW\n{q['review_note']}"
        display_text(self.detail,text)
        self.edit_button.configure(state='normal' if q['active'] else 'disabled')
        self.approve_button.configure(state='normal' if q['active'] and q['review_status']!='approved' else 'disabled')
        self.archive_button.configure(state='normal',text='Archive' if q['active'] else 'Restore')

    def add(self):
        self.editor=QuestionEditor(self,self.repo,self.refresh)

    def edit(self):
        q=self.selected()
        if q and q['active']:self.editor=QuestionEditor(self,self.repo,self.refresh,q)

    def approve(self):
        q=self.selected()
        if not q:return
        if not messagebox.askyesno('Approve this question?',f"Confirm that you reviewed {q['id']}: question, answer, marks and difficulty.\n\n"+q['prompt'][:250]+('\n\nThis sample keeps its demo origin.' if q['is_demo'] else ''),parent=self):return
        name=simpledialog.askstring('Reviewer','Your name for the review note:',parent=self)
        if name is None:return
        try:
            saved=self.repo.approve_question(q['id'],q['revision'],name)
        except BankError as exc:
            messagebox.showerror('Approval not saved',str(exc),parent=self);return
        self.refresh(saved['id'],'Approved '+saved['id']+'.'+(' Demo origin remains.' if saved['is_demo'] else ''))

    def archive(self):
        q=self.selected()
        if not q:return
        action='Archive' if q['active'] else 'Restore'
        detail='The question will be excluded from selection; it can be restored later.' if q['active'] else 'Restored questions return to draft and need review again.'
        if not messagebox.askyesno(action+' question?',f"{action} {q['id']}?\n\n{detail}",parent=self):return
        try:
            self.repo.set_archived(q['id'],q['active'],q['revision'])
        except BankError as exc:
            messagebox.showerror(action+' not saved',str(exc),parent=self);return
        self.refresh(q['id'],action+' completed for '+q['id']+'.')

    def import_csv(self):
        path=filedialog.askopenfilename(parent=self,title='Choose question CSV',filetypes=[('CSV files','*.csv'),('All files','*.*')])
        if path:ImportDialog(self,self.repo,path,self.refresh)

    def template(self):
        path=filedialog.asksaveasfilename(parent=self,title='Save question template',initialfile='Question_Import_Template.csv',defaultextension='.csv',filetypes=[('CSV files','*.csv')])
        if not path:return
        try:save_template(path)
        except OSError as exc:messagebox.showerror('Template not saved',str(exc),parent=self);return
        self.status.set('Saved CSV template: '+path)
