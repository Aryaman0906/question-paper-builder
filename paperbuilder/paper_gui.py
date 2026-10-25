"""History and replacement controls for the existing Tkinter application."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from .papers import list_papers, replacement_candidates, replace_question
from .storage import BankError


def question_text(q):
    lines = [q['id'] + ' | ' + q['unit'] + ' | ' + q['kind'] + ' | ' + q['difficulty'],
             f"{q['marks']} marks", '', q['prompt']]
    lines += [f"{o['id']}. {o['text']}" for o in q['options']]
    lines += ['', 'Answer:', q['answer'], '', 'Marking guidance:', q['rubric']]
    if q.get('correct_option_id'):
        lines += ['Correct option: ' + q['correct_option_id']]
    return '\n'.join(lines)


class ReplacementDialog(tk.Toplevel):
    def __init__(self, parent, repository, paper, number, on_apply):
        # Read first, so a failed bank read cannot leave a half-created modal window.
        candidates = replacement_candidates(paper, number, repository.questions())
        super().__init__(parent)
        self.repo, self.paper, self.number, self.on_apply = repository, paper, number, on_apply
        self.candidates = {q['id']: q for q in candidates}
        self.title(f'Replace question {number}'); self.transient(parent)
        self.geometry('780x650'); self.minsize(560, 440)
        box = ttk.Frame(self, padding=14); box.pack(fill='both', expand=True)
        ttk.Label(box, text='Only unused eligible questions with the same subject, unit, type, marks and difficulty appear.',
                  wraplength=710).pack(anchor='w', pady=(0,8))
        tabs = ttk.Notebook(box); tabs.pack(fill='both', expand=True)
        self.views = []
        for label in ('Current question', 'Replacement preview'):
            frame = ttk.Frame(tabs); tabs.add(frame, text=label)
            view = ScrolledText(frame, wrap='word', font=('Consolas', 10))
            view.pack(fill='both', expand=True); self.views.append(view)
        self.show(self.views[0], question_text(paper['items'][number-1]['question']))
        row = ttk.Frame(box); row.pack(fill='x', pady=8)
        ttk.Label(row, text='Replacement ID').pack(side='left')
        self.choice = tk.StringVar()
        combo = ttk.Combobox(row, textvariable=self.choice, values=list(self.candidates), state='readonly')
        combo.pack(side='left', fill='x', expand=True, padx=8)
        combo.bind('<<ComboboxSelected>>', lambda _: self.preview())
        self.tabs = tabs
        self.error = tk.StringVar(value=f'{len(candidates)} compatible alternatives.')
        ttk.Label(box, textvariable=self.error, wraplength=710).pack(anchor='w', pady=5)
        controls = ttk.Frame(box); controls.pack(fill='x')
        self.apply_button = ttk.Button(controls, text='Apply replacement', command=self.apply, state='disabled')
        self.apply_button.pack(side='right')
        ttk.Button(controls, text='Cancel', command=self.destroy).pack(side='left')
        if candidates:
            self.choice.set(candidates[0]['id']); self.preview(); self.apply_button.configure(state='normal')
        else:
            self.show(self.views[1], 'No compatible unused questions are available. Add and approve matching questions in the bank, then reopen this dialog.')
        self.bind('<Escape>', lambda _: self.destroy()); self.grab_set()

    @staticmethod
    def show(view, text):
        view.configure(state='normal'); view.delete('1.0', 'end'); view.insert('1.0', text); view.configure(state='disabled')

    def preview(self):
        self.show(self.views[1], question_text(self.candidates[self.choice.get()]))
        self.tabs.select(1)

    def apply(self):
        try:
            updated = replace_question(self.repo, self.paper, self.number, self.candidates[self.choice.get()])
        except (BankError, sqlite3.Error) as exc:
            self.error.set(str(exc)); self.apply_button.configure(state='disabled'); return
        self.on_apply(updated); self.destroy()


class HistoryPanel(ttk.Frame):
    def __init__(self, parent, repository, on_open):
        super().__init__(parent); self.pack(fill='both', expand=True)
        self.repo, self.on_open = repository, on_open
        ttk.Label(self, text='Saved papers are exact, read-only snapshots. Create a revision to replace questions without changing the original.',
                  wraplength=900).pack(anchor='w', pady=(0,10))
        table = ttk.Frame(self); table.pack(fill='both', expand=True)
        columns = ('title', 'mode', 'created', 'id')
        self.tree = ttk.Treeview(table, columns=columns, show='headings', selectmode='browse')
        for name, heading, width in zip(columns, ('Title', 'Mode', 'Created (UTC)', 'Paper ID'), (300, 100, 220, 300)):
            self.tree.heading(name, text=heading); self.tree.column(name, width=width, minwidth=80)
        y = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        x = ttk.Scrollbar(table, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        self.tree.grid(row=0,column=0,sticky='nsew'); y.grid(row=0,column=1,sticky='ns'); x.grid(row=1,column=0,sticky='ew')
        table.rowconfigure(0,weight=1); table.columnconfigure(0,weight=1)
        controls = ttk.Frame(self); controls.pack(fill='x', pady=10)
        ttk.Button(controls, text='Refresh history', command=self.refresh).pack(side='left')
        self.open_button = ttk.Button(controls, text='Open paper', command=lambda:self.open(False), state='disabled')
        self.open_button.pack(side='left', padx=8)
        self.revision_button = ttk.Button(controls, text='Create revision', command=lambda:self.open(True), state='disabled')
        self.revision_button.pack(side='left')
        self.status = tk.StringVar(); ttk.Label(self,textvariable=self.status,wraplength=900).pack(anchor='w')
        self.tree.bind('<<TreeviewSelect>>', lambda _:self.selection_changed())
        self.tree.bind('<Double-1>', lambda _:self.open(False))
        self.tree.bind('<Return>', lambda _:self.open(False))
        self.refresh()

    def selection_changed(self):
        state = 'normal' if self.tree.selection() else 'disabled'
        self.open_button.configure(state=state); self.revision_button.configure(state=state)

    def refresh(self, selected=None):
        try:
            rows = list_papers(self.repo)
        except sqlite3.Error as exc:
            self.status.set('Cannot read history: ' + str(exc)); return
        selected = selected or next(iter(self.tree.selection()), None)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert('', 'end', iid=r['id'], values=(r['title'], 'DEMO ONLY' if r['is_demo'] else 'Production', r['created_at'], r['id']))
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected); self.tree.see(selected)
        self.selection_changed()
        self.status.set(f'{len(rows)} saved papers. Revisions appear as separate entries; open one to see its parent ID. Open a paper to export its student PDF or teacher key from Review.')

    def open(self, revision):
        selection = self.tree.selection()
        if selection:
            self.on_open(selection[0], revision)
