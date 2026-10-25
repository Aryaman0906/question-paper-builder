"""Backup preview, explicit restore confirmation and recovery-copy reporting."""
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .backups import BackupError, create_backup, prepare_restore, restore_backup


def summary_text(summary):
    return (f"Questions: {summary['questions']} ({summary['archived']} archived)\n"
            f"Blueprint templates: {summary['blueprints']}\n"
            f"Selection rows: {summary['blueprint_rows']}\n"
            f"Saved papers and revisions: {summary['papers']}")


class BackupDialog(tk.Toplevel):
    def __init__(self, parent, repository):
        super().__init__(parent)
        self.repo, self.parent = repository, parent
        self.title('Backup and restore'); self.transient(parent); self.resizable(False, False)
        box = ttk.Frame(self, padding=18); box.pack(fill='both', expand=True)
        ttk.Label(box, text='Database: ' + str(repository.path.resolve()), wraplength=600).pack(anchor='w', pady=(0,12))
        ttk.Label(box, text='Backups contain saved questions, templates, papers and teacher answers. Unsaved paper or blueprint edits are not included.',
                  wraplength=600).pack(anchor='w', pady=(0,12))
        ttk.Button(box, text='Create database backup', command=self.backup).pack(anchor='w', pady=6)
        ttk.Label(box, text='Restore replaces the current database contents; it does not merge them. Close other copies of the app first. A recovery copy is created automatically. After a successful restore this app closes; reopen it to use the restored data.',
                  wraplength=600).pack(anchor='w', pady=12)
        ttk.Button(box, text='Choose backup to restore', command=self.restore).pack(anchor='w', pady=6)
        self.status = tk.StringVar()
        ttk.Label(box, textvariable=self.status, wraplength=600).pack(anchor='w', pady=12)
        ttk.Button(box, text='Close', command=self.destroy).pack(anchor='e')
        self.bind('<Escape>', lambda _:self.destroy()); self.grab_set()

    def backup(self):
        path = filedialog.asksaveasfilename(parent=self, title='Save database backup with a new filename',
            defaultextension='.sqlite3', initialfile='QuestionPaperBuilder-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.sqlite3',
            filetypes=[('SQLite backup', '*.sqlite3'), ('Backup', '*.bak')], confirmoverwrite=False)
        if not path: return
        self.configure(cursor='watch'); self.update_idletasks()
        try:
            summary = create_backup(self.repo, path)
            self.status.set('Backup saved: ' + path + '\n' + summary_text(summary))
        except BackupError as exc:
            messagebox.showerror('Cannot create backup', str(exc), parent=self)
        finally:
            self.configure(cursor='')

    def restore(self):
        path = filedialog.askopenfilename(parent=self, title='Choose a Question Paper Builder backup',
            filetypes=[('Database backups', '*.sqlite3 *.db *.bak'), ('All files', '*.*')])
        if not path: return
        self.configure(cursor='watch'); self.update_idletasks()
        try:
            with prepare_restore(path, self.repo.path) as prepared:
                self.configure(cursor='')
                confirmed = messagebox.askyesno('Replace database and close app?',
                    'Validated backup:\n' + str(prepared.source_path) + '\n\n' + summary_text(prepared.summary) +
                    '\n\nThis replaces all current saved database contents and discards unsaved paper/blueprint edits. '
                    'A recovery backup of current saved data will be kept beside your database. '
                    'Close all other copies of this app before continuing. Restore and close this app?', parent=self)
                if not confirmed: return
                self.configure(cursor='watch'); self.update_idletasks()
                recovery = restore_backup(self.repo, prepared)
            messagebox.showinfo('Restore complete', 'The database was restored. Reopen the app.\n\nRecovery backup:\n' + str(recovery), parent=self)
            self.parent.destroy()
        except BackupError as exc:
            messagebox.showerror('Cannot restore backup', str(exc), parent=self)
        finally:
            try:
                if self.winfo_exists(): self.configure(cursor='')
            except tk.TclError:
                pass  # Successful restore has destroyed the application.
