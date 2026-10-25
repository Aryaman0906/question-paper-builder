# Question Paper Builder

**Version 0.2.0 — Phase 2: question-bank management and CSV import**  
Aryaman Kundra · Roll number 2445591  
Assigned project: Question Paper Generation & Difficulty Balancing System

This release implements the next checklist milestone, scheduled for **24–25 October**, following the completed 22–23 October foundations. It is a working question-bank increment; paper generation and PDF export are still later milestones.

## Start on Windows

1. Extract the entire ZIP into a new folder. Keep `main.py`, `paperbuilder` and `data` together.
2. Open a terminal inside the extracted `question_paper_builder` folder.
3. Check that your Python installation has Tk:

```powershell
py -3.12 -m tkinter
```

4. Close the test window, then run:

```powershell
py -3.12 main.py
```

You can also double-click `run_windows.bat`. No pip packages are needed. If the launcher is unavailable, use your installed `python` executable for both `python -m tkinter` and `python main.py`. In VS Code, select that same interpreter. If Tk is missing, repair the Python installation with Tcl/Tk support; do not install a pip package named tkinter.

## What works in this release

- Search and filter questions by subject, unit, review status and active/archive state.
- Add and edit Short answer, Coding and four-option MCQ questions in a native GUI.
- Preserve multiline question text, code indentation, model answers and marking guidance.
- Validate required fields, positive whole marks, MCQ options and duplicate IDs/prompts.
- Approve questions with a reviewer name; content edits reset approval to draft.
- Archive and restore records; restored records need review again.
- Save a CSV template, preview every imported row, see errors and import a valid batch atomically.
- Detect stale edits from another app window and prevent accidental overwrites.
- Check the example 40-mark blueprint with optional demo samples.

All new or imported records begin as drafts. Approval records a review note; it is a local workflow, not a login or identity-verification system. Difficulty is a human estimate, not an empirically calibrated score. The 40 bundled demo records retain their demo origin even if edited or approved and remain excluded from production-only availability checks.

## Try the question-bank workflow

1. Open **Question bank → Add question**. Complete Details and Question and answer. For MCQs, also fill all four options and the correct option.
2. Save. Inspect the draft's answer and marking guidance, then choose **Approve** and enter the reviewer's name.
3. Edit the answer and save: its status becomes Draft again.
4. Archive it, switch Show to Archived, then restore it: it returns as a draft.
5. Choose **Import CSV**, open `data/Example_Questions.csv`, inspect all three rows and select **Import all as drafts**.
6. Open `data/Invalid_Example_Do_Not_Import.csv`: import stays disabled because a row has negative marks. Use a fresh test database if you want to isolate this error from duplicate-ID errors after step 5.

The supplied CSV examples are original sample material for testing and review. They are not teacher-approved exam content. Import does not execute any Python text in a question or answer.

## Upgrading from Phase 1

Close the old app before opening this release. The default database location is unchanged:

- Windows: `%LOCALAPPDATA%\QuestionPaperBuilder\demo_v1.sqlite3`
- Other platforms: `~/.local/share/QuestionPaperBuilder/demo_v1.sqlite3`

The legacy filename is retained to preserve your work. On the first open, schema version 1 is copied to a timestamped `.before-v2-…bak` file beside the database, then upgraded to version 2 with per-question revision numbers. Existing content and archive/review states are retained. Do not use the old app to edit the upgraded database. Keep the backup until you have checked your records. A general backup/restore GUI belongs to a later milestone.

Data is outside the source folder. Startup adds missing demonstration IDs without overwriting existing records. No personal/live database is included in this ZIP.

## Tests and a separate demo database

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 main.py --check --db .\test_demo.sqlite3
py -3.12 main.py --db .\practice.sqlite3
```

`--check` validates the example blueprint; it does not generate a paper. Exit codes: 0 success, 1 availability failure, 2 startup/database/display error.

**47 automated tests passed on Python 3.12.14.** Source compilation and GUI-module imports passed. Native windows could not be displayed in the build environment; Windows launch, resizing, scaling and keyboard checks are still required. User satisfaction has not yet been measured. See `docs/TEST_RESULTS.md` for the manual checklist and acceptance targets.

## Documents and next phase

- `docs/MILESTONE_24_25.md`: this phase's deliverables and completion checklist.
- `docs/CSV_IMPORT.md`: format, limits, error handling and examples.
- `docs/TEST_RESULTS.md`: automated evidence and manual acceptance checklist.
- `docs/DESIGN.md`: schema, migration and future generation contracts.
- `docs/SCOPE.md`, `docs/BANK_REVIEW.md`: scope and sample question coverage.
- `docs/MILESTONE_22_23.md`, `docs/GUI_WIREFRAMES.html`: historical Phase 1 evidence/design sketches.

**Next: 26–27 October — editable blueprints and difficulty-balanced paper generation.** Review/replacement/history, separate student/answer-key PDFs, backup/restore and final user acceptance follow. The final project report and submission ZIP are not yet complete.
