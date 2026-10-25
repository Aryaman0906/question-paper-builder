# Phase 2 — question-bank management

Scheduled milestone: 24–25 October 2026. Implemented on 23 October 2026 at the user's request to continue. Student: Aryaman Kundra, 2445591.

## Implementation checklist

- [x] Add/edit GUI with Details, Question and answer, and MCQ options tabs.
- [x] Preserve multiline question, code and answer text.
- [x] Validate required fields, marks, types, difficulty and MCQ mapping.
- [x] Prevent duplicate IDs and active exact-prompt duplicates.
- [x] New/imported records are drafts; content edits reset approval.
- [x] Record reviewer name/date and protect demo-origin flags.
- [x] Archive/restore with confirmation; restore requires review.
- [x] Search/filter by subject, unit, review and archive state.
- [x] Provide CSV template and sample files.
- [x] Preview complete rows with file/row errors before writes.
- [x] Atomic import, current-state revalidation and bounded file size/count.
- [x] Persist data and prevent stale edits from overwriting newer work.
- [x] Back up schema-v1 database before migrating to v2.
- [x] Add regression tests and Windows setup/upgrade instructions.
- [ ] Run native desktop visual and keyboard acceptance checks.
- [ ] Measure ease of use and satisfaction with representative users.

## Quality decisions

Use standard-library Tkinter/ttk and SQLite for an offline Python application without pip dependencies in this milestone. New screens call shared services and validators. Imported Python text is stored as text and never run by the application. A content edit invalidates review; a no-op save preserves it. Archive is reversible and does not free the stable question ID.

The UI provides plain error messages, retained form entries after failure, confirmation for discard/archive/import and a template to reduce formatting mistakes. These are implemented usability features; effectiveness still needs observed user testing.

## Evidence and limits

47 automated tests passed: 16 foundations plus 31 Phase 2 tests. They cover normal flows, invalid rows, duplicate records, stale previews, concurrent edits, transaction rollback and database migration. GUI imports and compilation are checked; no desktop display was available for actual rendering. See TEST_RESULTS.md for outstanding acceptance work.

Paper generation, editable saved blueprints, paper replacement/history and PDF export remain scheduled for later phases. Approval is a local review note, not authenticated role enforcement. The original demonstration-bank difficulty labels still require instructor calibration.

## Primary implementation references

- Python CSV module: https://docs.python.org/3.12/library/csv.html — DictReader/DictWriter, newline handling and CSV exceptions.
- Python sqlite3 module: https://docs.python.org/3.12/library/sqlite3.html — transactions, connection context managers and backup API.
- Tkinter dialogs: https://docs.python.org/3.12/library/dialog.html — file and simple-input dialogs.
- Tk themed widgets: https://docs.python.org/3.12/library/tkinter.ttk.html — notebook, combobox and treeview.

These references inform implementation; no outside question-bank material was copied. This phase extends the earlier council-reviewed checklist; no new council review is claimed for this code release.
