# Project updates

## Phase 3 — Editable blueprints and balanced generation (26–27 October objectives)

Implemented on 25 October 2026.

- Added paper metadata, instructions, difficulty targets and ordered row editing.
- Added atomic save/load of new blueprint template copies in the existing schema.
- Added unique fixed-group selection with aggregated demand and optional seeds.
- Rechecked every generated paper independently against row counts, eligibility, marks and difficulty.
- Added separate student/teacher previews, demo labelling and achieved balance summaries.
- Added a headless demo-generation command and expanded tests from 47 to 75.
- GUI rendering and user satisfaction remain unverified; temporary previews are not saved to paper history.

## Phase 2 — Question-bank GUI and CSV import (24–25 October objectives)

Implemented on 23 October at the student's request to continue ahead of the planned dates.

- Added GUI forms for Short answer, Coding and MCQ questions.
- Added search/filter, approval, archive and restore workflows.
- Made new/imported questions drafts and reset approval after content edits.
- Added CSV templates, full previews, row errors and atomic imports.
- Added duplicate detection, stale-edit checks and schema-v1 backup/migration.
- Expanded automated coverage to 47 tests, all passing in the release checks.
- Added sample CSVs, Windows instructions and acceptance checklists.

Native GUI rendering and user satisfaction remain unverified. Next: editable blueprints and difficulty-balanced generation; PDF export follows later.

## Phase 1 — Foundations (22–23 October objectives)

- Defined scope, GUI screen sketches and the database design.
- Added the Tkinter navigation shell and SQLite sample-bank persistence.
- Included 40 original demonstration questions with model answers and rubrics.
- Added exact blueprint totals, difficulty targets and availability validation.
- Delivered 16 automated foundation tests.

Native GUI rendering and Windows usability checks remain pending. Paper generation and PDF export are not implemented in this phase.
