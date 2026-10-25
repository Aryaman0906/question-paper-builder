# Question Paper Builder

**Version 0.1.0 — the 22–23 October foundation milestone**  
Aryaman Kundra · Roll number 2445591  
Assigned project: Question Paper Generation & Difficulty Balancing System

This is a runnable starter and design package, not the completed submission. It includes the frozen first-version scope, navigable Tkinter screen sketches, SQLite schema, tested blueprint rules and 40 original demonstration questions with model answers and rubrics.

## Start on Windows

1. Extract the entire ZIP. Keep `main.py`, `paperbuilder` and `data` together.
2. Open a terminal in the extracted `question_paper_builder` folder.
3. Check the interpreter and Tk installation:

```powershell
py -3.12 -m tkinter
```

4. Close the Tk test window, then run:

```powershell
py -3.12 main.py
```

Alternatively, double-click `run_windows.bat` if Python 3.12 is registered with the Windows launcher. No pip packages are needed for this milestone. Tkinter comes with the standard Windows Python installer when Tcl/Tk support is selected.

If `py` is unavailable, use your working Python executable directly:

```powershell
python -c "import sys; print(sys.executable)"
python -m tkinter
python main.py
```

Use the same interpreter for all three commands. In VS Code, choose that interpreter with **Python: Select Interpreter**. Do not install a pip package named tkinter to repair a missing Tk installation.

## What you can do now

- Browse, filter and inspect 40 sample questions and their marking guidance.
- View a six-row blueprint for a 40-mark, 13-question paper.
- Change total marks, time or difficulty percentages to examine validation.
- Check available questions and exact shortages for each selection group.
- Navigate all planned screens; unfinished actions are visibly disabled.
- Close and reopen without duplicate seeding or overwriting existing question edits.

The application starts in a clearly labelled **demo workspace**. Sample questions have `demo_reviewed` status, not instructor approval. Ordinary production eligibility excludes them; the prototype's availability check explicitly enables demo content.

## What is intentionally unfinished

Question editing/approval/archiving, CSV import, editable blueprint rows and saved templates, actual question selection, paper review/replacement, saved-paper services, PDF export, backup/restore, packaging as an EXE, and user acceptance testing. These belong to the subsequent checklist milestones.

Do not use this starter to prepare a real exam yet.

## Explore the documents

- `docs/MILESTONE_22_23.md`: completed objectives, evidence and limitations.
- `docs/SCOPE.md`: frozen scope, decisions and acceptance criteria.
- `docs/GUI_WIREFRAMES.html`: open in a browser for seven static screen sketches.
- `docs/DESIGN.md`: data model, layers, snapshot contract and generator plan.
- `docs/BANK_REVIEW.md`: demonstration-bank coverage and review method.
- `docs/TEST_RESULTS.md`: recorded verification and remaining manual checks.

## Test without opening a window

From the project folder:

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 main.py --check
```

`--check` validates the demonstration blueprint against the sample bank; it does not generate a paper. It exits with 0 on success and 1 for validation/availability failure.

To use a separate test database:

```powershell
py -3.12 main.py --check --db .\test_demo.sqlite3
```

The application uses a dedicated demo database by default:

- Windows: `%LOCALAPPDATA%\QuestionPaperBuilder\demo_v1.sqlite3`
- Other platforms: `~/.local/share/QuestionPaperBuilder/demo_v1.sqlite3`

Data is separate from the source folder. Startup adds missing sample IDs but never overwrites existing records. The ZIP contains JSON fixtures, not a personal or live exam database.

## Development status

16 automated foundation tests passed on Python 3.12.14. Coding model answers were exercised with trusted local fixtures. Tkinter imports and source compilation were checked. **The actual GUI window was not launched or visually tested here because this environment has no display server. Windows launch, scaling and keyboard usability remain manual checks.** The HTML screen sketches are design references, not screenshots of a tested application.

Next planned milestone: **24–25 October — question-bank editing, approval, archive and validated CSV import.**
