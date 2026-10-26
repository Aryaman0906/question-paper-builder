"""Real Tk integration checks. Requires a desktop or virtual X display.

These supplement headless workflow tests; they do not claim Windows DPI or
native file-dialog verification. No user's database or output files are used.
"""
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from paperbuilder.gui import Application
from paperbuilder.storage import Repository, demo_blueprint
from paperbuilder.blueprints import save_blueprint
from paperbuilder.generation import preview_text
from paperbuilder.papers import load_paper
from paperbuilder.question_bank import QuestionEditor, ImportDialog
from paperbuilder.backup_gui import BackupDialog
from paperbuilder.paper_gui import ReplacementDialog


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            root = tk.Tk(); root.destroy()
        except tk.TclError as exc:
            raise unittest.SkipTest('A Tk display is required: ' + str(exc))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Repository(Path(self.temp.name) / 'test.sqlite3')
        self.repo.seed_demo()
        self.root = tk.Tk()
        self.root.tk.call('tk', 'scaling', 96 / 72)
        self.callbacks = []
        self.root.report_callback_exception = lambda *error: self.callbacks.append(error)
        self.app = Application(self.root, self.repo)
        self.root.update()

    def tearDown(self):
        self.root.destroy(); self.repo.close(); self.temp.cleanup()
        self.assertEqual(self.callbacks, [], 'Unexpected exception in a Tk callback')

    def generate(self):
        self.app.include_demo.set(True); self.app.seed.set('42')
        self.assertTrue(self.app.check())
        self.app.generate_button.invoke(); self.root.update()

    def test_navigation_and_dashboard_reflect_saved_data(self):
        self.assertEqual(self.app.stat_values['questions'].get(), '40')
        self.assertEqual(self.app.stat_values['approved'].get(), '0')
        question = dict(self.repo.questions()[0], id='USER-1', prompt='A unique reviewed question?')
        question = self.repo.create_question(question)
        self.repo.approve_question(question['id'], question['revision'], 'Instructor')
        save_blueprint(self.repo, demo_blueprint())
        self.generate(); self.app.save_button.invoke()
        self.app.nav_buttons['Home'].invoke(); self.root.update()
        self.assertEqual({key: value.get() for key, value in self.app.stat_values.items()},
                         dict(questions='41', approved='1', templates='1', papers='1'))
        for title, button in self.app.nav_buttons.items():
            button.invoke(); self.root.update()
            self.assertEqual(self.app.notebook.select(), str(self.app.pages[title]))
            self.assertEqual(self.app.page_title.get(), self.app.page_descriptions[title][0])
            self.assertEqual(button.cget('style'), 'Active.Nav.TButton')

    def test_styled_previews_and_revision_keep_exact_snapshot(self):
        self.generate()
        snapshot = self.app.paper
        self.assertEqual(self.app.student_text.get('1.0', 'end-1c'), preview_text(snapshot))
        self.assertEqual(self.app.teacher_text.get('1.0', 'end-1c'), preview_text(snapshot, teacher=True))
        self.assertTrue(self.app.student_text.tag_ranges('heading'))
        self.assertTrue(self.app.student_text.tag_ranges('warning'))
        self.app.save_button.invoke(); self.root.update()
        self.assertTrue(self.app.save_button.instate(['disabled']))
        self.assertTrue(self.app.replace_button.instate(['disabled']))
        self.app.revision_button.invoke(); self.root.update()
        self.assertEqual(self.app.paper['parent_paper_id'], snapshot['paper_id'])
        self.assertFalse(self.app.paper_saved)
        self.assertEqual(load_paper(self.repo, snapshot['paper_id']), snapshot)
        with patch('paperbuilder.gui.messagebox.askyesno', return_value=False):
            revision = self.app.paper
            self.app.open_saved(snapshot['paper_id'])
            self.assertIs(self.app.paper, revision)

    def test_bank_filters_empty_state_and_details(self):
        panel = self.app.bank_panel
        self.app.go('Question bank'); self.root.update()
        panel.query.set('no matching question text'); self.root.update()
        self.assertEqual(panel.tree.get_children(), ())
        self.assertIn('No questions match', panel.detail.get('1.0', 'end'))
        panel.clear_filters(); self.root.update()
        self.assertEqual(len(panel.tree.get_children()), 40)
        first = panel.tree.get_children()[0]
        panel.tree.selection_set(first); self.root.update()
        self.assertIn(self.repo.get(first)['answer'], panel.detail.get('1.0', 'end'))
        self.assertTrue(panel.edit_button.instate(['!disabled']))
        self.assertEqual(tuple(panel.tree.cget('displaycolumns'))[:2], ('id', 'prompt'))

    def test_help_topics_and_navigation_do_not_change_work(self):
        original = self.repo.questions()
        blueprint = self.app.setup_panel.raw()
        self.app.go('Help'); self.root.update()
        panel = self.app.help_panel
        for topic, button in panel.topic_buttons.items():
            button.invoke(); self.root.update()
            self.assertEqual(panel.current_topic.get(), topic)
            self.assertTrue(panel.article.winfo_children())
        panel.show_topic('start'); self.root.update()
        actions = [w for w in panel.article.winfo_children() if w.winfo_class() == 'TButton']
        actions[0].invoke(); self.root.update()
        self.assertEqual(self.app.notebook.select(), str(self.app.pages['Question bank']))
        self.assertEqual(self.repo.questions(), original)
        self.assertEqual(self.app.setup_panel.raw(), blueprint)
        self.assertIsNone(self.app.paper)

    def test_empty_studio_becomes_exact_preview_and_history_keeps_identity(self):
        self.app.go('Review'); self.root.update()
        self.assertTrue(self.app.review_empty.winfo_ismapped())
        self.assertFalse(self.app.review_content.winfo_ismapped())
        self.generate()
        self.assertFalse(self.app.review_empty.winfo_ismapped())
        self.assertTrue(self.app.review_content.winfo_ismapped())
        self.assertEqual(self.app.student_text.get('1.0', 'end-1c'), preview_text(self.app.paper))
        self.app.save_current()
        identifier = self.app.paper['paper_id']
        self.app.go('Saved papers'); self.root.update()
        self.app.history.tree.selection_set(identifier); self.root.update()
        self.assertIn(identifier, self.app.history.selected_detail.get())
        self.assertEqual(self.app.history.tree.item(identifier, 'values')[-1], identifier)
        self.assertEqual(load_paper(self.repo, identifier), self.app.paper)

    def test_small_window_overflow_keeps_actions_reachable(self):
        self.root.geometry('960x680'); self.root.update()
        for title in self.app.pages:
            self.app.go(title); self.root.update()
            page = self.app.pages[title]
            self.assertGreaterEqual(page.body.winfo_width(), page.body.winfo_reqwidth())
            self.assertGreaterEqual(page.body.winfo_height(), page.body.winfo_reqheight())
        self.app.go('Availability'); self.root.update()
        page = self.app.pages['Availability']
        page.reveal(self.app.generate_button); self.root.update()
        top = self.app.generate_button.winfo_rooty() - page.canvas.winfo_rooty()
        self.assertGreaterEqual(top, 0)
        self.assertLessEqual(top + self.app.generate_button.winfo_height(), page.canvas.winfo_height())

    def test_dialog_content_and_cancel_preserve_bank(self):
        original = self.repo.questions()
        editor = QuestionEditor(self.root, self.repo, lambda *_: None, original[0])
        self.root.update(); editor.tabs.select(1); self.root.update()
        self.assertEqual(editor.texts['answer'].get('1.0', 'end-1c'), original[0]['answer'])
        editor.cancel(); self.root.update()
        dialog = BackupDialog(self.root, self.repo); self.root.update()
        dialog.destroy(); self.root.update()
        self.assertEqual(self.repo.questions(), original)

    def test_enlarged_text_keeps_replacement_and_rubric_accessible(self):
        self.root.destroy()
        self.root = tk.Tk(); self.root.tk.call('tk', 'scaling', 144 / 72)
        self.root.report_callback_exception = lambda *error: self.callbacks.append(error)
        self.app = Application(self.root, self.repo); self.root.update()
        self.generate()
        dialog = ReplacementDialog(self.root, self.repo, self.app.paper, 1, lambda *_: None)
        self.root.update()
        button = dialog.apply_button
        self.assertTrue(button.winfo_ismapped())
        self.assertLessEqual(button.winfo_rooty() + button.winfo_height(),
                             dialog.winfo_rooty() + dialog.winfo_height())
        dialog.destroy()
        editor = QuestionEditor(self.root, self.repo, lambda *_: None, self.repo.questions()[0])
        editor.tabs.select(1); self.root.update()
        page = editor.editor_pages[1]
        page.reveal(editor.texts['rubric']); self.root.update()
        top = editor.texts['rubric'].winfo_rooty() - page.canvas.winfo_rooty()
        self.assertGreaterEqual(top, 0)
        self.assertLess(top, page.canvas.winfo_height())
        editor.cancel()
        path = Path(__file__).resolve().parents[1] / 'data' / 'Example_Questions.csv'
        dialog = ImportDialog(self.root, self.repo, path, lambda *_: None)
        dialog.geometry('760x520'); self.root.update()
        button = dialog.commit_button
        self.assertTrue(button.winfo_ismapped())
        self.assertLessEqual(button.winfo_rooty() + button.winfo_height(),
                             dialog.winfo_rooty() + dialog.winfo_height())
        dialog.destroy()


if __name__ == '__main__':
    unittest.main()
