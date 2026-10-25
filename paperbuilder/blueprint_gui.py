"""Blueprint editor, ordered selection rows and saved template picker."""
from collections import Counter
from copy import deepcopy
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from .blueprints import save_blueprint, load_blueprint, list_blueprints
from .storage import BankError, demo_blueprint
from .validation import blueprint_errors, KINDS, DIFFICULTIES


def whole_number(text):
    text = text.strip()
    return int(text) if text.isascii() and text.isdigit() and len(text) <= 9 else text


class RowEditor(tk.Toplevel):
    def __init__(self, parent, row, on_save):
        super().__init__(parent)
        self.title('Selection row'); self.transient(parent.winfo_toplevel())
        self.resizable(False, False); self.on_save = on_save
        box = ttk.Frame(self, padding=18); box.pack(fill='both', expand=True)
        self.vars = {}
        defaults = dict(section='A', unit='', kind='Short answer', difficulty='Easy', marks=2, count=1)
        defaults.update(row or {})
        for i, (field, label) in enumerate((('section','Section'),('unit','Unit / module'),('kind','Question type'),
                                           ('difficulty','Difficulty'),('marks','Marks per question'),('count','Number of questions'))):
            ttk.Label(box,text=label).grid(row=i,column=0,sticky='w',padx=(0,12),pady=7)
            var=tk.StringVar(value=str(defaults[field]));self.vars[field]=var
            if field in ('kind','difficulty'):
                w=ttk.Combobox(box,textvariable=var,values=KINDS if field=='kind' else DIFFICULTIES,state='readonly',width=24)
            else:
                w=ttk.Entry(box,textvariable=var,width=26)
            w.grid(row=i,column=1,sticky='ew',pady=7)
        self.error=tk.StringVar()
        ttk.Label(box,textvariable=self.error,foreground='#9b2d20',wraplength=400).grid(row=6,column=0,columnspan=2,pady=8)
        ttk.Button(box,text='Apply row',command=self.save).grid(row=7,column=1,sticky='e')
        ttk.Button(box,text='Cancel',command=self.cancel).grid(row=7,column=0,sticky='w')
        self.original=self.state_values()
        self.protocol('WM_DELETE_WINDOW',self.cancel);self.bind('<Escape>',lambda _:self.cancel());self.grab_set()

    def state_values(self):
        return tuple(v.get() for v in self.vars.values())

    def cancel(self):
        if self.state_values()!=self.original and not messagebox.askyesno('Discard row changes?','Discard the unsaved changes to this row?',parent=self):
            return False
        self.destroy();return True

    def save(self):
        row={k:v.get().strip() for k,v in self.vars.items()}
        for f in ('marks','count'):row[f]=whole_number(row[f])
        if not row['section'] or not row['unit'] or any(type(row[f]) is not int or row[f]<=0 for f in ('marks','count')):
            self.error.set('Enter section, unit, positive whole marks and a positive whole count.');return
        if row['count']>1000:
            self.error.set('A paper can contain at most 1,000 questions.');return
        self.on_save(row);self.destroy()


class BlueprintPanel(ttk.Frame):
    def __init__(self,parent,repository,on_change,on_check):
        super().__init__(parent);self.pack(fill='both',expand=True)
        self.repo=repository;self.on_change=on_change;self.loading=True;self.row_editor=None
        top=ttk.Frame(self);top.pack(fill='x',pady=(0,8))
        self.saved=tk.StringVar();self.saved_map={}
        self.saved_combo=ttk.Combobox(top,textvariable=self.saved,state='readonly',width=35)
        self.saved_combo.pack(side='left',fill='x',expand=True)
        ttk.Button(top,text='Load',command=self.load_saved).pack(side='left',padx=4)
        ttk.Button(top,text='Refresh list',command=self.refresh_saved).pack(side='left')
        ttk.Button(top,text='Save as new template',command=self.save).pack(side='left',padx=4)
        tabs=ttk.Notebook(self);tabs.pack(fill='both',expand=True)
        details=ttk.Frame(tabs,padding=12);selection=ttk.Frame(tabs,padding=10)
        tabs.add(details,text='Paper details');tabs.add(selection,text='Selection rows')
        details.columnconfigure(1,weight=1);self.vars={}
        for i,(field,label) in enumerate((('title','Paper title'),('subject','Subject'),('total_marks','Total marks'),('duration_minutes','Time (minutes)'))):
            ttk.Label(details,text=label).grid(row=i,column=0,sticky='w',pady=5,padx=(0,12))
            var=tk.StringVar();self.vars[field]=var
            ttk.Entry(details,textvariable=var).grid(row=i,column=1,sticky='ew',pady=5)
        targets=ttk.Frame(details);targets.grid(row=4,column=0,columnspan=2,sticky='ew',pady=8)
        for i,d in enumerate(DIFFICULTIES):
            ttk.Label(targets,text=d+' %').grid(row=0,column=2*i,padx=5)
            var=tk.StringVar();self.vars[d]=var
            ttk.Entry(targets,textvariable=var,width=8).grid(row=0,column=2*i+1,padx=5)
        ttk.Label(details,text='Instructions for students').grid(row=5,column=0,columnspan=2,sticky='w')
        self.instructions=ScrolledText(details,height=3,wrap='word',undo=True)
        self.instructions.grid(row=6,column=0,columnspan=2,sticky='nsew',pady=5);details.rowconfigure(6,weight=1)
        ttk.Label(details,text='Difficulty percentages are shares of marks. They must total 100; allocated row marks must match exactly.',wraplength=700).grid(row=7,column=0,columnspan=2,sticky='w',pady=5)
        table=ttk.Frame(selection);table.pack(fill='both',expand=True)
        columns=('section','unit','kind','difficulty','marks','count','subtotal')
        self.tree=ttk.Treeview(table,columns=columns,show='headings',selectmode='browse',height=7)
        for key,width in zip(columns,(75,140,130,85,75,75,85)):
            self.tree.heading(key,text=key.title());self.tree.column(key,width=width,minwidth=50)
        y=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview);x=ttk.Scrollbar(table,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        self.tree.grid(row=0,column=0,sticky='nsew');y.grid(row=0,column=1,sticky='ns');x.grid(row=1,column=0,sticky='ew')
        table.columnconfigure(0,weight=1);table.rowconfigure(0,weight=1)
        self.tree.bind('<Double-1>',lambda _:self.edit_row())
        controls=ttk.Frame(selection);controls.pack(fill='x',pady=10)
        for text,command in (('Add row',self.add_row),('Edit row',self.edit_row),('Remove',self.remove_row),('Move up',lambda:self.move(-1)),('Move down',lambda:self.move(1))):
            ttk.Button(controls,text=text,command=command).pack(side='left',padx=(0,5))
        self.summary=tk.StringVar();ttk.Label(self,textvariable=self.summary,wraplength=1000).pack(anchor='w',pady=6)
        bottom=ttk.Frame(self);bottom.pack(fill='x')
        ttk.Button(bottom,text='New blank',command=self.new_blank).pack(side='left')
        ttk.Button(bottom,text='Load demo blueprint',command=self.load_demo).pack(side='left',padx=6)
        ttk.Button(bottom,text='Check availability',command=on_check).pack(side='right')
        self.status=tk.StringVar(value='Demo blueprint loaded. Generation excludes demo questions unless you opt in.')
        ttk.Label(self,textvariable=self.status,wraplength=1000).pack(anchor='w',pady=(6,0))
        for var in self.vars.values():var.trace_add('write',lambda *_:self.changed())
        self.instructions.bind('<<Modified>>',self.text_changed)
        self.set_blueprint(demo_blueprint());self.refresh_saved()

    def text_changed(self,_=None):
        if self.instructions.edit_modified():
            self.instructions.edit_modified(False);self.changed()

    def raw(self):
        return (tuple(v.get() for v in self.vars.values()),self.instructions.get('1.0','end-1c'),deepcopy(self.rows))

    def dirty(self):
        return self.raw()!=self.baseline

    def confirm_replace(self):
        return not self.dirty() or messagebox.askyesno('Discard blueprint edits?','Load another blueprint and discard these unsaved edits?',parent=self)

    def set_blueprint(self,bp):
        self.loading=True
        for key,var in self.vars.items():
            var.set(str(bp['difficulty_percent'][key] if key in DIFFICULTIES else bp[key]))
        self.instructions.delete('1.0','end');self.instructions.insert('1.0',bp.get('instructions',''));self.instructions.edit_modified(False)
        self.rows=deepcopy(bp['rows']);self.redraw();self.baseline=self.raw();self.loading=False;self.changed()

    def blueprint(self):
        bp={k:self.vars[k].get().strip() for k in ('title','subject')}
        bp.update({k:whole_number(self.vars[k].get()) for k in ('total_marks','duration_minutes')})
        bp['difficulty_percent']={d:self.vars[d].get().strip() for d in DIFFICULTIES}
        bp['instructions']=self.instructions.get('1.0','end-1c');bp['rows']=deepcopy(self.rows)
        return bp

    def changed(self):
        if self.loading:return
        marks=Counter();units=Counter()
        for row in self.rows:
            marks[row['difficulty']]+=row['marks']*row['count'];units[row['unit']]+=row['marks']*row['count']
        self.summary.set(f'Allocated: {sum(marks.values())} marks / {sum(r["count"] for r in self.rows)} questions | '+
                         ' | '.join(f'{d}: {marks[d]}' for d in DIFFICULTIES)+'\nUnits: '+', '.join(f'{u}: {m}' for u,m in units.items()))
        self.on_change()

    def redraw(self,select=None):
        self.tree.delete(*self.tree.get_children())
        for i,r in enumerate(self.rows):
            self.tree.insert('','end',iid=str(i),values=tuple(r[k] for k in ('section','unit','kind','difficulty','marks','count'))+(r['marks']*r['count'],))
        if select is not None and select<len(self.rows):self.tree.selection_set(str(select));self.tree.see(str(select))

    def selected(self):
        return int(self.tree.selection()[0]) if self.tree.selection() else None

    def add_row(self):
        if len(self.rows)>=100:
            messagebox.showerror('Row limit','Use at most 100 rows.',parent=self);return
        def apply(row):self.rows.append(row);self.redraw(len(self.rows)-1);self.changed()
        self.row_editor=RowEditor(self,None,apply)

    def edit_row(self):
        i=self.selected()
        if i is None:return
        def apply(row):self.rows[i]=row;self.redraw(i);self.changed()
        self.row_editor=RowEditor(self,self.rows[i],apply)

    def remove_row(self):
        i=self.selected()
        if i is not None and messagebox.askyesno('Remove row?',f'Remove selection row {i+1}?',parent=self):
            self.rows.pop(i);self.redraw(min(i,len(self.rows)-1) if self.rows else None);self.changed()

    def move(self,offset):
        i=self.selected()
        if i is not None and 0<=i+offset<len(self.rows):
            self.rows[i],self.rows[i+offset]=self.rows[i+offset],self.rows[i];self.redraw(i+offset);self.changed()

    def refresh_saved(self):
        try:
            self.saved_map={f'{b["title"]} | {b["id"][-8:]}':b['id'] for b in list_blueprints(self.repo)}
            self.saved_combo.configure(values=tuple(self.saved_map))
        except sqlite3.Error as exc:messagebox.showerror('Cannot list templates',str(exc),parent=self)

    def save(self):
        try:identifier=save_blueprint(self.repo,self.blueprint())
        except (BankError,sqlite3.Error) as exc:
            messagebox.showerror('Blueprint not saved',str(exc),parent=self);return
        self.baseline=self.raw();self.refresh_saved()
        self.saved.set(next(k for k,v in self.saved_map.items() if v==identifier))
        self.status.set('Saved a new template. Previous saved copies remain available.')

    def load_saved(self):
        identifier=self.saved_map.get(self.saved.get())
        if not identifier:
            self.status.set('Choose a saved template first.');return
        if not self.confirm_replace():return
        try:bp=load_blueprint(self.repo,identifier)
        except (BankError,sqlite3.Error) as exc:
            messagebox.showerror('Cannot load blueprint',str(exc),parent=self);return
        self.set_blueprint(bp);self.status.set('Loaded saved template. Save edits as a new template.')

    def load_demo(self):
        if self.confirm_replace():self.set_blueprint(demo_blueprint());self.status.set('Demo blueprint loaded; opt into demo questions on Availability to try it.')

    def new_blank(self):
        if not self.confirm_replace():return
        self.set_blueprint(dict(title='',subject='Python Programming',total_marks=40,duration_minutes=60,
                                difficulty_percent=dict(Easy=30,Medium=50,Hard=20),instructions='All questions are compulsory.',rows=[]))
        self.status.set('Blank blueprint: enter details and add selection rows.')
