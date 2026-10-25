# Question Paper Builder

**Version 0.5.1 — Phase 5: PDF export and database backup/restore**

Aryaman Kundra · Roll number 2445591  
Assigned project: Question Paper Generation & Difficulty Balancing System

This release implements the **30–31 October** checklist objectives, prepared on 25 October. It adds separate printable student/teacher PDFs and validated database backup/restore. The existing Tkinter workflow is retained. Final Windows acceptance, observed user testing, visual polish and the submission report remain to be completed.

## Windows saving fix (0.5.1)

Version 0.5.0 could fail both PDF export and database backup with `[Errno 9] Bad file descriptor` on Windows. The shared output helper flushed a read-only file handle. Version 0.5.1 opens it read/write without truncating the finished output. This also fixes the recovery-copy step used during restore. Download the updated code and restart the app; no database migration or dependency reinstall is required. The title bar shows 0.5.1.

Seven new regression tests cover writable flushing, both PDF exports, database backup/restore recovery and failure cleanup. The prior Linux-only tests missed Windows' write-access requirement. The new tests enforce that requirement on Linux; they are not a substitute for the pending Windows retest.

## Start on Windows

1. Clone this repository or use GitHub **Code → Download ZIP** and extract it. Keep `main.py`, `paperbuilder` and `data` together.
2. Open a terminal in the project folder containing `main.py`.
3. Check that your Python installation has Tk:

```powershell
py -3.12 -m tkinter
```

4. Close the test window, install PDF support once, then run:

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
```

You can also double-click `run_windows.bat`. If Windows Smart App Control blocks the downloaded batch file, keep the security setting enabled and use the terminal command above from the extracted project folder. ReportLab is needed for PDF export; the question bank, generation and backup features still work without it. A missing PDF dependency produces installation instructions when exporting. If the launcher is unavailable, use your installed `python` executable for both `python -m tkinter` and `python main.py`. In VS Code, select that same interpreter. If Tk is missing, repair the Python installation with Tcl/Tk support; do not install a pip package named tkinter.

## What works in this release

- Search and filter questions by subject, unit, review status and active/archive state.
- Add and edit Short answer, Coding and four-option MCQ questions in a native GUI.
- Preserve multiline question text, code indentation, model answers and marking guidance.
- Validate required fields, positive whole marks, MCQ options and duplicate IDs/prompts.
- Approve questions with a reviewer name; content edits reset approval to draft.
- Archive and restore records; restored records need review again.
- Save a CSV template, preview every imported row, see errors and import a valid batch atomically.
- Detect stale edits from another app window and prevent accidental overwrites.
- Edit paper title, subject, time, instructions and difficulty percentages.
- Add/edit/remove/reorder selection rows; save and reload blueprint templates.
- Check current shortages and generate matching questions without reuse.
- Inspect separate student and teacher previews, with exact marks/difficulty/unit summaries.
- Use an optional seed for repeatable initial selection under unchanged inputs.
- Preview and apply compatible unused replacement questions, preserving exact balance.
- Save complete papers and reopen their original questions, answers and blueprint after restart.
- Create separate revisions with parent IDs; existing saved papers remain read-only.
- Preserve the current paper when bank/setup settings change; warn before discarding unsaved work.
- Export separate A4 student papers and teacher keys, with page numbers and demo labels.
- Preserve code indentation and wrap long code lines with a visible continuation marker.
- Back up questions, templates, saved papers and revisions to a new database file.
- Preview and validate backups before restoring; create a recovery copy and roll back failed restores.

All new or imported records begin as drafts. Approval records a review note; it is a local workflow, not a login or identity-verification system. Difficulty is a human estimate, not an empirically calibrated score. The 40 bundled demo records retain their demo origin even if edited or approved and remain excluded from production-only availability checks.

## Try the question-bank workflow

1. Open **Question bank → Add question**. Complete Details and Question and answer. For MCQs, also fill all four options and the correct option.
2. Save. Inspect the draft's answer and marking guidance, then choose **Approve** and enter the reviewer's name.
3. Edit the answer and save: its status becomes Draft again.
4. Archive it, switch Show to Archived, then restore it: it returns as a draft.
5. Choose **Import CSV**, open `data/Example_Questions.csv`, inspect all three rows and select **Import all as drafts**.
6. Open `data/Invalid_Example_Do_Not_Import.csv`: import stays disabled because a row has negative marks. Use a fresh test database if you want to isolate this error from duplicate-ID errors after step 5.

The supplied CSV examples are original sample material for testing and review. They are not teacher-approved exam content. Import does not execute any Python text in a question or answer.

## Try Phase 3

1. Open **Paper setup**. Inspect **Paper details** and **Selection rows**. The example allocates 40 marks across 13 questions.
2. Choose **Save as new template**. The saved copy remains available after restart. Each save creates another copy; it never overwrites an existing template.
3. Go to **Availability**, enable **Demo mode**, and choose **Check blueprint**. Production mode is the default and correctly reports shortages until your own approved bank is large enough.
4. Optionally enter seed `42`, then **Generate paper**. Review the student paper and teacher key in separate tabs. All demo-mode papers are visibly labelled.
5. Verify the balance: **Easy 12, Medium 20, Hard 8 marks**; **Module 1: 18, Module 2: 22**. No question ID appears twice.
6. Change Total marks to `41` and check again. Generation is blocked with exact validation errors; your requirements are not rounded or silently changed.

Blueprints support up to 100 rows and papers up to 1,000 questions. The algorithm uses fixed unit/type/marks/difficulty groups. There are no flexible alternatives, optional questions or automatic difficulty estimates. Difficulty balance is based on teacher-assigned labels.

Editing setup, seed, mode or the bank now preserves the paper in **Review**, including its own original blueprint. Availability must be checked again for new generation. Another app instance does not send live notifications; generation and replacement read the current bank. Existing snapshot questions retain their historical content and review state. Saving does not reapprove them against the current bank.

## Try Phase 4

1. Generate a demo paper using the Phase 3 steps above.
2. In **Review**, choose a **Question no. → Replace question**. Inspect the Current question and Replacement preview tabs, choose an ID, then **Apply replacement**.
3. Check that only that question changed: the paper still has 13 unique questions, 40 marks and difficulty totals 12/20/8.
4. Click **Save paper**. The status becomes **Saved • read-only**; repeated saves do not create duplicates.
5. Close and reopen the app. In **Saved papers**, select the entry and **Open paper**. Both previews must match the saved contents exactly.
6. Select **Create revision** from history or the saved paper in Review. Replace a question and **Save paper**. Two separate entries now exist; opening either shows its own content. The revision shows its parent paper ID.
7. Edit or archive a bank question that appears in the original. Reopen the original and verify its text and key remain unchanged.
8. Leave a paper/revision unsaved, then try to open another or generate again. Choose **No** to keep it. Editing the bank or setup also keeps it. Closing the app asks before losing unsaved work.

Replacement matches subject, unit, question type, marks and difficulty exactly, excludes every ID already in the paper and obeys that paper's demo/production mode. If no alternatives exist, it explains the shortage; it does not loosen constraints. A candidate changed in another app window after preview is rejected; reopen the replacement list to inspect the new content. Saved revisions preserve the original blueprint, mode and initial seed; to change the blueprint, generate a new paper.

The generation seed describes the original selection, not manual replacements. History stores the full content instead of trying to regenerate it. Save is explicit: closing without saving loses the working copy. History stores teacher answers as well as student content; it is not an encrypted or access-controlled vault.

## Try Phase 5: PDFs

1. Open a saved paper from **Saved papers → Open paper**, or generate a new one.
2. In **Review**, choose **Export student PDF**, then select a filename.
3. Choose **Export teacher key PDF** and use a separate filename. The key includes answers, marking guidance, IDs and difficulty totals; the student PDF omits those fields.
4. Open both PDFs and check every page. Print on A4 at actual size/100%. Demo-mode exports display the demo warning on every page.
5. Reopen a saved revision and export again: the exported content comes from that exact snapshot. Exporting an unsaved working paper does not automatically save it to history.

PDFs use fonts available on the computer, with bundled ReportLab fonts as a fallback for the demo's English text. Missing glyphs fail clearly rather than creating unreadable boxes. This exporter does not yet support complex scripts such as Hindi or Arabic; it is currently intended for the English Python project. Code indentation is retained, tabs display as four spaces, and long preformatted lines wrap with `> ` continuation. User-entered markup is printed literally. Short question/key blocks stay together when they fit; very long blocks can span pages.

## Try Phase 5: backup and restore

1. Save any paper/blueprint changes you want to keep.
2. Click **Backup / restore** at the top right, then **Create database backup**. Choose a new `.sqlite3` filename; existing backups are never overwritten.
3. The backup includes questions (including archived records/review state), blueprint templates/rows, saved papers and revisions. It includes teacher answers; it does not include unsaved edits, application source or previously exported PDFs.
4. To restore, close other copies of the app, select **Choose backup to restore**, and inspect the validated record counts. **No** cancels without changing data.
5. Confirm only when you intend to replace the entire current database; restore is not a merge. The app first creates a timestamped `.before-restore-…bak` beside the active database, then replaces all data in one transaction. Failures roll back the changes. Success closes this app; reopen it to see restored data.
6. To undo a successful restore, choose the reported recovery `.bak` file through the same restore flow.

Use a separate practice database for your first restore test. Only schema version 2 backups (Phase 2 onward), up to 200 MiB, are accepted. Wrong schemas, broken question/template/paper data and corrupt files are rejected. A private copy holds the exact validated contents shown in the confirmation, so subsequent changes to the source file do not change what is restored. Keep backups on another drive/location if you need protection against loss of the laptop or its disk. Backups are ordinary unencrypted SQLite databases.

## Upgrading from an earlier phase

Close the old app before opening this release. The default database location is unchanged:

- Windows: `%LOCALAPPDATA%\QuestionPaperBuilder\demo_v1.sqlite3`
- Other platforms: `~/.local/share/QuestionPaperBuilder/demo_v1.sqlite3`

Phase 5 uses the existing schema version 2 tables; no additional migration is needed from Phases 2–4. The legacy filename is retained to preserve your work. On the first open, schema version 1 is copied to a timestamped `.before-v2-…bak` file beside the database, then upgraded to version 2 with per-question revision numbers. Existing content and archive/review states are retained. Do not use the old app to edit the upgraded database. Keep the backup until you have checked your records. The general Backup / restore dialog is available in this release; it accepts schema version 2 backups.

Data is outside the source folder. Startup seeds demonstration questions only when creating a new database. Existing and restored databases are not silently refilled, including intentionally empty backups. No personal/live database is included in this ZIP.

## Tests and a separate demo database

```powershell
py -3.12 -m pip install -r requirements-dev.txt
py -3.12 -m unittest discover -s tests -v
py -3.12 main.py --check --db .\test_demo.sqlite3
py -3.12 main.py --generate-demo --seed 42 --db .\practice.sqlite3
py -3.12 main.py --db .\practice.sqlite3
```

`--check` validates the example blueprint. `--generate-demo` prints a complete demo snapshot as JSON, including teacher answers; it is not a student export. These modes are mutually exclusive. Exit codes: 0 success, 1 availability failure, 2 invalid input or startup/database/display error.

**171 automated tests passed on Python 3.12.14**, with ReportLab 4.4.9 and PDF verification dependencies installed. The new checks cover PDF audience separation, page bounds, indentation, literal markup, missing dependencies, backup integrity, WAL snapshots, cancelled restores, rollback after partial restore and recovery copies. Sample PDFs were rendered and inspected: 2 student pages and 4 teacher pages. Source compilation and GUI imports passed.

The user confirmed the main Phase 3 and Phase 4 workflows on Windows. New Phase 5 native dialogs have not been visually tested in this display-less build environment. Windows export/printing/restore interaction and scaling still require manual checks. User satisfaction has not been formally measured. PDF tests skip if development dependencies are absent; install `requirements-dev.txt` to run the full suite. See `docs/TEST_RESULTS.md`.

## Documents and next phase

- `docs/MILESTONE_30_31.md`: Phase 5 objectives, implementation and acceptance checklist.
- `docs/MILESTONE_28_29.md`: historical Phase 4 objectives and workflow.
- `docs/MILESTONE_26_27.md`: historical Phase 3 objectives, workflow and algorithm.
- `docs/MILESTONE_24_25.md`: historical Phase 2 checklist.
- `docs/CSV_IMPORT.md`: format, limits, error handling and examples.
- `docs/TEST_RESULTS.md`: automated evidence and manual acceptance checklist.
- `docs/DESIGN.md`: schema, migration and future generation contracts.
- `docs/SCOPE.md`, `docs/BANK_REVIEW.md`: scope and sample question coverage.
- `docs/MILESTONE_22_23.md`, `docs/GUI_WIREFRAMES.html`: historical Phase 1 evidence/design sketches.

**Next: final Windows acceptance, observed user testing and visual polish.** The final project report and submission ZIP are not yet complete.
