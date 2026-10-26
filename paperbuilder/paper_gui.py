"""History and replacement controls for the existing Tkinter application."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, font
from .ui import ScrolledText, stripe_tree, decorate_text
from .papers import list_papers, replacement_candidates, replace_question
from .storage import BankError
from .presentation import format_timestamp


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
        box.columnconfigure(0,weight=1);box.rowconfigure(1,weight=1)
        ttk.Label(box, text='Only unused eligible questions with the same subject, unit, type, marks and difficulty appear.',
                  wraplength=710).grid(row=0,column=0,sticky='ew',pady=(0,8))
        tabs = ttk.Notebook(box); tabs.grid(row=1,column=0,sticky='nsew')
        self.views = []
        for label in ('Current question', 'Replacement preview'):
            frame = ttk.Frame(tabs); tabs.add(frame, text=label)
            view = ScrolledText(frame, height=10, wrap='word', font=('Consolas', 10))
            view.pack(fill='both', expand=True); self.views.append(view)
        self.show(self.views[0], question_text(paper['items'][number-1]['question']))
        row = ttk.Frame(box); row.grid(row=2,column=0,sticky='ew',pady=8)
        ttk.Label(row, text='Replacement ID').pack(side='left')
        self.choice = tk.StringVar()
        combo = ttk.Combobox(row, textvariable=self.choice, values=list(self.candidates), state='readonly')
        combo.pack(side='left', fill='x', expand=True, padx=8)
        combo.bind('<<ComboboxSelected>>', lambda _: self.preview())
        self.tabs = tabs
        self.error = tk.StringVar(value=f'{len(candidates)} compatible alternatives.')
        ttk.Label(box, textvariable=self.error, wraplength=710).grid(row=3,column=0,sticky='ew',pady=5)
        controls = ttk.Frame(box); controls.grid(row=4,column=0,sticky='ew')
        self.apply_button = ttk.Button(controls, text='Apply replacement', style='Primary.TButton', command=self.apply, state='disabled')
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
        decorate_text(view)

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
        ttk.Label(self, text='Your saved papers, ready to reopen or revise.',
                  style='Section.TLabel').pack(anchor='w', pady=(0,4))
        ttk.Label(self, text='Saved copies stay unchanged. A revision lets you replace questions while keeping the original.',
                  style='Muted.TLabel', wraplength=760).pack(anchor='w', pady=(0,16))
        table = ttk.Frame(self); table.pack(fill='both', expand=True)
        table.configure(width=680,height=340);table.grid_propagate(False)
        columns = ('title', 'mode', 'created', 'id')
        self.tree = ttk.Treeview(table, columns=columns, displaycolumns=('title', 'mode', 'created'),
                                 show='headings', selectmode='browse')
        for name, heading, width in zip(columns, ('Paper title', 'Mode', 'Saved at (UTC)', 'Paper ID'), (360, 150, 240, 300)):
            self.tree.heading(name, text=heading, anchor='w'); self.tree.column(name, width=width, minwidth=80)
        self.tree.column('mode', stretch=False)
        self.tree.column('created', width=font.nametofont('TkDefaultFont').measure('26 Oct 2026 · 23:59 UTC') + 32, stretch=False)
        y = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        x = ttk.Scrollbar(table, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        self.tree.grid(row=0,column=0,sticky='nsew'); y.grid(row=0,column=1,sticky='ns'); x.grid(row=1,column=0,sticky='ew')
        table.rowconfigure(0,weight=1); table.columnconfigure(0,weight=1)
        summary = ttk.Frame(self, style='Panel.TFrame', padding=16)
        summary.pack(fill='x', pady=(12,0))
        self.selected_title = tk.StringVar(value='Select a saved paper')
        self.selected_detail = tk.StringVar(value='Choose a row to see its details and available actions.')
        ttk.Label(summary, textvariable=self.selected_title, style='CardTitle.TLabel',
                  wraplength=740).pack(anchor='w')
        ttk.Label(summary, textvariable=self.selected_detail, style='CardMuted.TLabel',
                  wraplength=740).pack(anchor='w', pady=(6,0))
        summary.bind('<Configure>', lambda event: [child.configure(wraplength=max(240, event.width - 32))
                                                    for child in summary.winfo_children()])
        controls = ttk.Frame(self); controls.pack(fill='x', pady=12)
        self.open_button = ttk.Button(controls, text='Open paper', style='Primary.TButton', command=lambda:self.open(False), state='disabled')
        self.open_button.pack(side='left')
        self.revision_button = ttk.Button(controls, text='Create revision', command=lambda:self.open(True), state='disabled')
        self.revision_button.pack(side='left', padx=8)
        ttk.Button(controls, text='Refresh history', command=self.refresh).pack(side='right')
        self.status = tk.StringVar(); ttk.Label(self,textvariable=self.status,style='Muted.TLabel',wraplength=760).pack(anchor='w')
        self.rows_by_id = {}
        self.tree.bind('<<TreeviewSelect>>', lambda _:self.selection_changed())
        self.tree.bind('<Double-1>', lambda _:self.open(False))
        self.tree.bind('<Return>', lambda _:self.open(False))
        self.refresh()

    def selection_changed(self):
        selection = self.tree.selection()
        state = 'normal' if selection else 'disabled'
        self.open_button.configure(state=state); self.revision_button.configure(state=state)
        row = self.rows_by_id.get(selection[0]) if selection else None
        if row:
            self.selected_title.set(row['title'])
            mode = 'Demonstration paper' if row['is_demo'] else 'Production paper'
            self.selected_detail.set(f"{mode} · Saved {format_timestamp(row['created_at'])}\nPaper ID: {row['id']}")
        else:
            self.selected_title.set('Select a saved paper' if self.rows_by_id else 'Your paper collection starts here')
            self.selected_detail.set('Open a paper to review it and export student or teacher PDFs.' if self.rows_by_id
                                     else 'Generate a paper, then choose Save paper in Paper studio. It will appear here.')

    def refresh(self, selected=None):
        try:
            rows = list_papers(self.repo)
        except sqlite3.Error as exc:
            self.status.set('Cannot read history: ' + str(exc)); return
        selected = selected or next(iter(self.tree.selection()), None)
        self.rows_by_id = {row['id']: row for row in rows}
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert('', 'end', iid=r['id'], values=(r['title'], 'Demo only' if r['is_demo'] else 'Production', format_timestamp(r['created_at']), r['id']))
        stripe_tree(self.tree)
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected); self.tree.see(selected)
        self.selection_changed()
        count = len(rows)
        self.status.set('No saved papers yet.' if not rows else
                        f'{count} saved {"paper" if count == 1 else "papers"} · Revisions appear as separate entries. Open a revision to see its parent ID.')

    def open(self, revision):
        selection = self.tree.selection()
        if selection:
            self.on_open(selection[0], revision)
