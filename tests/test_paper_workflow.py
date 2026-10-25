"""Headless controller checks for data-loss boundaries; not visual Tk tests."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from paperbuilder.gui import Application
from paperbuilder.storage import Repository, BankError, demo_blueprint
from paperbuilder.generation import generate_paper
from paperbuilder.papers import save_paper


class PaperWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Repository(Path(self.temp.name)/'test.sqlite3'); self.repo.seed_demo()
        self.app = Application.__new__(Application)
        app = self.app
        app.repo = self.repo; app.root = Mock()
        app.paper = generate_paper(demo_blueprint(), self.repo.questions(), True, 42)
        app.paper_saved = False
        app.generate_button = Mock(); app.set_text = Mock(); app.result = Mock()
        app.show_paper = Mock(); app.go = Mock(); app.history = Mock()
        app.setup_panel = Mock(); app.setup_panel.dirty.return_value = False
        app.setup_panel.blueprint.return_value = demo_blueprint()
        app.setup_panel.row_editor = None
        app.bank_panel = Mock(); app.bank_panel.editor = None
        app.seed = Mock(); app.seed.get.return_value = '42'
        app.include_demo = Mock(); app.include_demo.get.return_value = True
        self.ask = patch('paperbuilder.gui.messagebox.askyesno', return_value=False).start()
        self.error = patch('paperbuilder.gui.messagebox.showerror').start()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        self.repo.close(); self.temp.cleanup()

    def test_bank_or_setup_change_preserves_unsaved_snapshot(self):
        original = self.app.paper
        self.app.invalidate()
        self.assertIs(self.app.paper, original)
        self.assertFalse(self.app.paper_saved)
        self.app.generate_button.configure.assert_called_once_with(state='disabled')
        self.app.show_paper.assert_not_called()

    def test_declining_open_preserves_unsaved_paper(self):
        identifier = save_paper(self.repo, self.app.paper)
        self.app.open_saved(identifier)
        self.ask.assert_called_once(); self.app.show_paper.assert_not_called()

    def test_failed_open_keeps_current_paper_without_discard_prompt(self):
        original = self.app.paper
        self.app.open_saved('missing')
        self.error.assert_called_once(); self.ask.assert_not_called()
        self.assertIs(self.app.paper, original)
        self.app.show_paper.assert_not_called()

    def test_saved_open_does_not_warn_about_unsaved_paper(self):
        identifier = save_paper(self.repo, self.app.paper); self.app.paper_saved = True
        self.app.open_saved(identifier)
        self.ask.assert_not_called()
        self.app.show_paper.assert_called_once_with(self.app.paper, saved=True)

    def test_declining_generate_keeps_current_paper(self):
        self.app.generate()
        self.app.show_paper.assert_not_called(); self.ask.assert_called_once()

    def test_failed_generation_after_confirmation_keeps_current_paper(self):
        original = self.app.paper
        self.ask.return_value = True; self.app.seed.get.return_value = 'bad seed'
        self.app.generate()
        self.assertIs(self.app.paper, original)
        self.app.show_paper.assert_not_called()

    def test_failed_save_retains_unsaved_state(self):
        original = self.app.paper
        with patch('paperbuilder.gui.save_paper', side_effect=BankError('disk failure')):
            self.app.save_current()
        self.error.assert_called_once(); self.app.show_paper.assert_not_called()
        self.assertIs(self.app.paper, original); self.assertFalse(self.app.paper_saved)
        self.app.history.refresh.assert_not_called()

    def test_unsaved_close_can_be_cancelled(self):
        self.app.close()
        self.ask.assert_called_once(); self.app.root.destroy.assert_not_called()

    def test_saved_paper_and_clean_blueprint_close_without_warning(self):
        self.app.paper_saved = True
        self.app.close()
        self.ask.assert_not_called(); self.app.root.destroy.assert_called_once()

    def test_saved_paper_does_not_hide_unsaved_blueprint(self):
        self.app.paper_saved = True; self.app.setup_panel.dirty.return_value = True
        self.app.close()
        self.ask.assert_called_once(); self.app.root.destroy.assert_not_called()


if __name__ == '__main__':
    unittest.main()
