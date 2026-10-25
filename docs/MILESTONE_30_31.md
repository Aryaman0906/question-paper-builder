# Phase 5 — PDF export and backup/restore

Planned objectives: 30–31 October 2026. Implemented early on 25 October at the student's request. Version 0.5.0.

## Completed functionality

- [x] Export a separate A4 student question paper and teacher answer key from Review.
- [x] Re-export exact saved papers/revisions without reading changed bank content.
- [x] Keep teacher-only fields out of student PDF content and metadata.
- [x] Preserve code indentation, paginate long content and label every demo page.
- [x] Report missing PDF dependency, unsupported text and output failures without losing work.
- [x] Confirm PDF overwrite; protect non-PDF files and stage new output before publishing.
- [x] Back up all persisted question/template/paper data through SQLite's backup API.
- [x] Validate a private restore snapshot and show counts before explicit replacement confirmation.
- [x] Create a recovery copy before restoring; use a single transaction and rollback on failure.
- [x] Close the app after a successful restore; retain exact restored contents on next startup.
- [x] Run 164 automated tests and inspect rendered PDF samples.
- [ ] Verify new controls and printing on the user's Windows laptop.
- [ ] Complete representative-user trials and record actual ease/satisfaction results.

## Start and use

Install PDF support with `py -3.12 -m pip install -r requirements.txt`, then launch `py -3.12 main.py`. Open or generate a paper and use the two export buttons in Review. Exporting does not save an unsaved paper to history.

Use the top-right Backup / restore button for saved data. Give each backup a new filename. Restore is whole-database replacement, not a merge; close other app copies and inspect the confirmation. A recovery `.bak` appears next to the active database, and can be selected through the same restore flow to undo a restore. The first restore trial should use a separate practice database.

## Limits

ReportLab 4.4.9 is the tested PDF dependency. English and covered glyphs are supported; complex scripts such as Hindi/Arabic are rejected until shaping support is added. Tabs display as four spaces and long code lines use a visible continuation prefix. Backups are unencrypted, include teacher answers, and exclude unsaved edits/exported PDFs. Restore accepts schema version 2 up to 200 MiB and does not enforce a global single-app lock.

## Next

Windows functional acceptance, user trials, visual polish, final report and submission packaging. Earlier user confirmation of Phase 4 does not verify Phase 5's new controls. See TEST_RESULTS.md for the precise acceptance checklist and evidence.
