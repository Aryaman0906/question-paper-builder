# Project updates

## 0.5.1 — Windows PDF/backup saving fix

- Fix `[Errno 9] Bad file descriptor` reported by the user on both PDF export and database backup.
- Open the completed temporary file as `r+b` before fsync. Windows requires write access; existing bytes remain intact.
- The shared fix also covers pre-restore recovery backups; no schema or dependency changes.
- Reproduced four failures with a Windows-style writable-handle regression guard before the fix; all 171 tests pass after it.
- Windows GUI retest is pending; the build environment remains Linux.

## Phase 5 — PDF export and database backup/restore (30–31 October objectives)

Implemented on 25 October 2026. Version 0.5.0.

- Added separate A4 student/teacher exports with safe audience field selection, literal text, code indentation, pagination and demo labels.
- Added ReportLab as an optional-at-runtime PDF dependency; installation errors are actionable and do not stop other features.
- Stage exports before publishing, confirm PDF overwrite and preserve existing files on failure.
- Added SQLite online backups including committed WAL data, validation and non-overwriting output names.
- Added restore preview, explicit replacement confirmation, private stable snapshot and automatic pre-restore recovery copy.
- Restore all four data tables in one transaction; rollback on failure and close the GUI only after success.
- Seed demo records only for newly created databases, preserving exact restored/empty state.
- Expanded automated tests from 114 to 164. Rendered/inspected 2-page student and 4-page teacher examples.
- User confirmed Phase 4 functionality on Windows. Phase 5 native GUI/printing acceptance remains pending.
- PDF complex-script support, formal usability results, visual redesign and final submission materials remain incomplete.

## Phase 4 — Replacement, saved papers and revisions (28–29 October objectives)

Implemented on 25 October 2026. Version 0.4.0.

- Added exact compatible replacement with current-bank rechecking and candidate previews.
- Added atomic, retry-safe snapshot saves and saved-paper history in existing schema version 2.
- Added read-only reopening and new revision copies with parent IDs; saved content is never overwritten.
- Validate snapshot envelopes and stored metadata; reject corrupted, unsupported and mismatched records.
- Preserve working papers during bank/setup changes and protect unsaved work when switching or closing.
- Render deterministic, readable balance summaries so reopen preserves both previews exactly.
- Expanded tests from 75 to 114, including replacement races, restart equality and unsaved-work boundaries.
- User confirmed Phase 3 launch/generation/template persistence on Windows. Phase 4 visual interaction and satisfaction checks remain pending.
- PDF export, backup/restore and visual redesign remain later work.

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
