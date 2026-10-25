"""Headless UI guards; these tests do not render native dialogs."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
from paperbuilder.gui import Application
from paperbuilder.backup_gui import BackupDialog
from paperbuilder.storage import Repository, demo_blueprint
from paperbuilder.generation import generate_paper
from paperbuilder.backups import create_backup, BackupError
from paperbuilder.pdf_export import ExportError


class Phase5WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.directory=Path(self.temp.name)
        self.repo=Repository(self.directory/'bank.sqlite3');self.repo.seed_demo()
        self.app=Application.__new__(Application)
        self.app.root=Mock();self.app.repo=self.repo
        self.app.paper=generate_paper(demo_blueprint(),self.repo.questions(),True,42)
        self.app.paper_saved=False
        self.save_dialog=patch('paperbuilder.gui.filedialog.asksaveasfilename',return_value='').start()
        self.open_dialog=patch('paperbuilder.backup_gui.filedialog.askopenfilename',return_value='').start()
        self.ask=patch('paperbuilder.gui.messagebox.askyesno',return_value=False).start()
        self.error=patch('paperbuilder.gui.messagebox.showerror').start()
        self.info=patch('paperbuilder.gui.messagebox.showinfo').start()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        self.repo.close();self.temp.cleanup()

    def dialog(self):
        dialog=BackupDialog.__new__(BackupDialog)
        dialog.repo=self.repo;dialog.parent=self.app.root
        dialog.configure=Mock();dialog.update_idletasks=Mock();dialog.winfo_exists=Mock(return_value=True)
        return dialog

    def test_cancel_export_has_no_side_effects(self):
        original=deepcopy(self.app.paper)
        with patch('paperbuilder.gui.export_pdf') as export:
            self.app.export_current(False)
            export.assert_not_called()
        self.assertEqual(self.app.paper,original);self.assertFalse(self.app.paper_saved)

    def test_decline_overwrite_keeps_existing_file(self):
        target=self.directory/'student.pdf';target.write_bytes(b'%PDF-existing')
        self.save_dialog.return_value=str(target)
        with patch('paperbuilder.gui.export_pdf') as export:
            self.app.export_current(False);export.assert_not_called()
        self.assertEqual(target.read_bytes(),b'%PDF-existing')

    def test_failed_export_retains_paper_and_unsaved_state(self):
        self.save_dialog.return_value=str(self.directory/'teacher.pdf')
        original=deepcopy(self.app.paper)
        with patch('paperbuilder.gui.export_pdf',side_effect=ExportError('failed')):
            self.app.export_current(True)
        self.error.assert_called_once();self.info.assert_not_called()
        self.assertEqual(self.app.paper,original);self.assertFalse(self.app.paper_saved)

    def test_export_does_not_claim_unsaved_paper_was_saved_to_history(self):
        self.save_dialog.return_value=str(self.directory/'teacher.pdf')
        with patch('paperbuilder.gui.export_pdf') as export:
            self.app.export_current(True)
        self.assertTrue(export.call_args.kwargs['teacher'])
        self.assertIn('still unsaved',self.info.call_args.args[1])
        self.assertFalse(self.app.paper_saved)

    def test_export_cannot_target_active_database(self):
        self.save_dialog.return_value=str(self.repo.path)
        with patch('paperbuilder.gui.export_pdf') as export:
            self.app.export_current(False);export.assert_not_called()
        self.error.assert_called_once()

    def test_cancel_restore_confirmation_keeps_database_and_app(self):
        backup=self.directory/'backup.sqlite3';create_backup(self.repo,backup)
        self.open_dialog.return_value=str(backup)
        before=self.repo.questions()
        with patch('paperbuilder.backup_gui.restore_backup') as restore:
            self.dialog().restore();restore.assert_not_called()
        self.assertEqual(self.repo.questions(),before)
        self.app.root.destroy.assert_not_called()
        self.assertIn('discards unsaved',self.ask.call_args.args[1])

    def test_restore_failure_keeps_app_open(self):
        backup=self.directory/'backup.sqlite3';create_backup(self.repo,backup)
        self.open_dialog.return_value=str(backup);self.ask.return_value=True
        with patch('paperbuilder.backup_gui.restore_backup',side_effect=BackupError('rolled back')):
            self.dialog().restore()
        self.error.assert_called_once();self.app.root.destroy.assert_not_called()

    def test_successful_restore_closes_app_and_reports_recovery(self):
        backup=self.directory/'backup.sqlite3';create_backup(self.repo,backup)
        self.open_dialog.return_value=str(backup);self.ask.return_value=True
        self.dialog().restore()
        self.app.root.destroy.assert_called_once()
        self.assertIn('Recovery backup',self.info.call_args.args[1])
        self.assertEqual(len(list(self.directory.glob('*.bak'))),1)

    def test_invalid_backup_never_prompts_to_replace_or_closes_app(self):
        bad=self.directory/'bad.sqlite3';bad.write_bytes(b'not sqlite')
        self.open_dialog.return_value=str(bad)
        self.dialog().restore()
        self.ask.assert_not_called();self.app.root.destroy.assert_not_called();self.error.assert_called_once()


if __name__=='__main__': unittest.main()
