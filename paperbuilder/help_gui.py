"""Task-oriented, read-only guidance for the existing desktop workflow."""
import tkinter as tk
from tkinter import ttk

from . import __version__


class HelpPanel(ttk.Frame):
    """A small help centre; its parent ScrollPage handles page scrolling.

    Actions only navigate to existing pages. Selecting a help topic never
    changes a question, blueprint, paper or preference.
    """

    TOPICS = (
        ('start', 'Start here'),
        ('bank', 'Question bank'),
        ('blueprint', 'Blueprint & balance'),
        ('papers', 'Papers & revisions'),
        ('export', 'PDF & backups'),
        ('questions', 'Common questions'),
        ('shortcuts', 'Shortcuts & about'),
    )

    def __init__(self, parent, go):
        super().__init__(parent)
        self.pack(fill='both', expand=True)
        self.go = go
        self.current_topic = tk.StringVar(value='start')
        self.topic_buttons = {}
        self._wrapping = []
        ttk.Label(self, text='FIND YOUR WAY', style='Muted.TLabel').pack(anchor='w', pady=(0, 8))
        self.topic_bar = ttk.Frame(self)
        self.topic_bar.pack(fill='x', pady=(0, 16))
        for key, title in self.TOPICS:
            button = ttk.Button(self.topic_bar, text=title, width=17,
                                command=lambda topic=key: self.show_topic(topic))
            self.topic_buttons[key] = button
        self.article = ttk.Frame(self, style='Panel.TFrame', padding=22)
        self.article.pack(fill='x', anchor='n')
        self.bind('<Configure>', self._resize, add='+')
        self.show_topic('start')

    def _label(self, text, style='Card.TLabel', pady=(0, 10)):
        label = ttk.Label(self.article, text=text, style=style, justify='left', wraplength=400)
        label.pack(anchor='w', fill='x', pady=pady)
        self._wrapping.append(label)
        return label

    def _section(self, title, text):
        self._label(title, 'CardTitle.TLabel', (14, 6))
        self._label(text)

    def _action(self, label, destination):
        ttk.Button(self.article, text=label, style='Link.TButton',
                   command=lambda: self.go(destination)).pack(anchor='w', pady=(4, 10))

    def _resize(self, event=None):
        width = event.width if event is not None else self.winfo_width()
        if width <= 1:
            width = 660
        button_width = max(button.winfo_reqwidth() for button in self.topic_buttons.values())
        columns = max(1, min(4, width // (button_width + 8)))
        for index in range(4):
            self.topic_bar.columnconfigure(index, weight=1 if index < columns else 0,
                                           uniform='help-topics' if index < columns else '')
        for index, button in enumerate(self.topic_buttons.values()):
            button.grid(row=index // columns, column=index % columns, sticky='ew',
                        padx=(0, 8 if index % columns < columns - 1 else 0), pady=(0, 8))
        for label in self._wrapping:
            label.configure(wraplength=max(120, min(880, width - 48)))

    def show_topic(self, topic):
        if topic not in self.topic_buttons:
            raise ValueError('Unknown help topic: ' + str(topic))
        self.current_topic.set(topic)
        for key, button in self.topic_buttons.items():
            button.configure(style='Primary.TButton' if key == topic else 'TButton')
        for child in self.article.winfo_children():
            child.destroy()
        self._wrapping.clear()
        getattr(self, '_topic_' + topic)()
        self._resize()

    def _topic_start(self):
        self._label('Your first paper, in three steps', 'CardTitle.TLabel')
        self._label('Choose a topic above for focused guidance, or follow this short route to a finished paper.',
                    'CardMuted.TLabel')
        self._section('01  Prepare your question bank',
                      'Add questions or preview a CSV import. Check the questions, model answers and marking guidance, then approve the content you want to use.')
        self._action('Open question bank  →', 'Question bank')
        self._section('02  Build and check your blueprint',
                      'Set the title, subject, time and total marks in Paper setup. Add selection rows and difficulty targets, then check availability. The report shows exactly where more questions are needed.')
        self._action('Set up a paper  →', 'Paper setup')
        self._section('03  Review, save and export',
                      'Generate a paper from Check & generate. Review the student paper and teacher key in Paper studio, save a copy to history, then export the PDFs you need.')
        self._action('Check & generate  →', 'Availability')
        self._section('Trying the supplied sample?',
                      'Load the demo blueprint in Paper setup and enable Demo mode in Check & generate. Sample questions are for demonstration; use approved, non-demo questions for a real exam.')

    def _topic_bank(self):
        self._label('A question bank you can trust', 'CardTitle.TLabel')
        self._label('Keep content easy to find and ready for review.', 'CardMuted.TLabel')
        self._section('Find and review a question',
                      'Search or filter the bank, then select a question to read its full prompt, model answer and marking guidance. You can add, edit, approve, archive or restore questions.')
        self._section('Drafts and approval',
                      'New questions and imported questions start as drafts. Approve them with a review note after checking their content. Editing content resets approval. Restoring an archived question returns it to draft; its demo origin is retained.')
        self._section('Import with confidence',
                      'Save the CSV template, fill it in and preview your import. Use UTF-8, comma-separated files with at most 1,000 records and a maximum size of 2 MiB. If any row has an error, nothing is imported. Existing questions are never overwritten.')
        self._section('Your bank stays yours',
                      'Reopening the app does not duplicate or overwrite the seeded questions. Production generation uses active, approved, non-demo questions. Demo samples require an explicit opt-in.')
        self._action('Open question bank  →', 'Question bank')

    def _topic_blueprint(self):
        self._label('Give every mark a place', 'CardTitle.TLabel')
        self._label('A blueprint describes the paper you want to create.', 'CardMuted.TLabel')
        self._section('Paper details and selection rows',
                      'Set the paper details, then add, edit or reorder selection rows. Rows specify the matching questions you need. Save a blueprint template to reuse the structure later, or load an existing template.')
        self._section('Balance is measured in marks',
                      'Easy, Medium and Hard percentages are shares of marks, not question counts. They must total 100%, and the allocated row marks must match the paper total exactly. Difficulty labels are estimates for a target cohort; no AI calibration is claimed.')
        self._section('Check before generating',
                      'Check & generate shows the required, available and missing questions for each group. Generation selects unique matching questions and checks the current bank again. Changing the setup or bank means availability must be checked again.')
        self._section('Optional seed',
                      'Leave the seed blank for a fresh selection. A seed repeats selection only with the same eligible bank, blueprint and generator/runtime. Different seeds may still select the same questions. The seed describes initial generation, not later replacements.')
        self._action('Open paper setup  →', 'Paper setup')

    def _topic_papers(self):
        self._label('Review once. Return with confidence.', 'CardTitle.TLabel')
        self._label('Paper studio keeps the student paper and teacher key together, in separate previews.',
                    'CardMuted.TLabel')
        self._section('Inspect and refine',
                      'Review both previews and the balance totals. An unsaved paper can use a compatible replacement from the current bank: an unused eligible question with the same subject, unit, type, marks and difficulty. Marks and balance stay exact.')
        self._section('Save an exact copy',
                      'Save paper stores the blueprint, ordered questions, answers and marking guidance. Reopen that exact snapshot from Saved papers, even if questions in the bank have since been edited or archived. Existing snapshot content is historical.')
        self._section('Revise without losing the original',
                      'Saved papers are read-only. Create revision makes an unsaved copy linked to its parent paper. Save the revision to retain it; the original stays unchanged. Revisions appear as separate history entries.')
        self._section('Keep track of unsaved work',
                      'Changing the setup or bank preserves the paper in Paper studio. Generating another paper asks before discarding unsaved work. Save before closing if you want to keep your working paper.')
        self._action('Open saved papers  →', 'Saved papers')

    def _topic_export(self):
        self._label('Take your paper with you', 'CardTitle.TLabel')
        self._label('PDFs are for sharing. Backups protect your saved workspace.', 'CardMuted.TLabel')
        self._section('Export student and teacher copies',
                      'Open a paper in Paper studio and choose Export student PDF or Export teacher key PDF. These are separate printable A4 documents. Saved papers can be reopened and exported again.')
        self._section('Set up PDF support once',
                      'ReportLab is needed only for PDF export. From your project folder, run this command:')
        command = tk.StringVar(value='py -3.12 -m pip install -r requirements.txt')
        self.pdf_command = ttk.Entry(self.article, textvariable=command, state='readonly')
        self.pdf_command._value = command
        self.pdf_command.pack(fill='x', pady=(0, 10))
        self._section('Text and code in PDFs',
                      'Exports preserve code indentation. Long code lines use > continuation; tabs display as four spaces. Fonts must cover the text. Complex scripts, including Hindi and Arabic, are not supported by this exporter yet.')
        self._section('Back up saved work',
                      'Use Backup / restore in the sidebar to create a database backup. It includes saved questions, templates, papers and teacher answers. Unsaved edits and exported PDFs are not included. Choose a new backup filename each time; existing backups are never overwritten.')
        self._section('Restore carefully',
                      'Restore replaces the current database contents; it does not merge them. Close other copies of the app first. A validated restore creates a recovery backup, then closes the app. Reopen it to refresh every screen and use the restored data.')
        self._action('Open paper studio  →', 'Review')

    def _topic_questions(self):
        self._label('A quick answer can keep you moving', 'CardTitle.TLabel')
        self._label('Common questions about the existing workflow.', 'CardMuted.TLabel')
        self._section('Why is Generate paper unavailable?',
                      'Run Check blueprint after changing the setup or bank. Resolve the errors and shortages in the availability report. If you are trying the supplied demo blueprint, enable Demo mode or add enough approved, non-demo questions.')
        self._section('Why is my question not being selected?',
                      'Check that it is active, approved and matches the blueprint row. Demo questions are excluded unless Demo mode is enabled. Each selected question is used only once in a paper.')
        self._section('Why can’t I edit a saved paper?',
                      'Saved copies are intentionally read-only. Choose Create revision to work on a new copy, then save the revision. Your original paper remains available.')
        self._section('Why are there no replacement options?',
                      'A replacement must be unused and match the current question’s subject, unit, type, marks and difficulty. Add and approve another matching question in the bank, then reopen the replacement dialog.')
        self._section('Does exporting a PDF save the paper to history?',
                      'No. Choose Save paper to retain the working paper in history. Export creates a separate PDF file; it does not save an unsaved paper to the database.')
        self._section('Why did the same seed give a different result?',
                      'Repeatable selection also depends on the eligible bank, blueprint and generator/runtime. To return to an exact paper, save it and reopen its snapshot instead of relying on the seed.')

    def _topic_shortcuts(self):
        self._label('Small shortcuts, a smoother day', 'CardTitle.TLabel')
        self._label('Use the keyboard to move around your workspace.', 'CardMuted.TLabel')
        for key, action in (('Ctrl + 1', 'Overview'), ('Ctrl + 2', 'Question bank'),
                            ('Ctrl + 3', 'Paper setup'), ('Ctrl + 4', 'Check & generate'),
                            ('Ctrl + 5', 'Paper studio'), ('Ctrl + 6', 'Saved papers'),
                            ('Ctrl + 7', 'Help & guidance'),
                            ('Tab / Shift + Tab', 'Move forward / backward through controls')):
            row = ttk.Frame(self.article, style='Card.TFrame')
            row.pack(fill='x', pady=4)
            ttk.Label(row, text=key, style='Badge.TLabel', width=19).pack(side='left')
            label = ttk.Label(row, text=action, style='Card.TLabel', wraplength=250)
            label.pack(side='left', padx=14)
        self._section('About this workspace',
                      'Question Paper Builder ' + __version__ + '. A local desktop workspace for question banks, blueprints, paper review and export. ReportLab is needed only for PDF export.')

