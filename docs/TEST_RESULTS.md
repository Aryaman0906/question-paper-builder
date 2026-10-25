# Phase 3 verification record

Date: 25 October 2026. Runtime: Python 3.12.14. Platform: Linux build environment.

```text
python -m unittest discover -s tests -v
```

**Result: 75 tests passed (16 foundations, 31 Phase 2, 28 Phase 3).**

| Area | Verified behavior |
|---|---|
| Foundations | 40 valid sample questions; 40 marks/13 questions; exact percentages and group shortages; repeated-group aggregation; immutable snapshot schema; trusted sample coding-answer fixtures. |
| Persistence | Records survive reopening; repeated demo seeding preserves content and review state. |
| Review | Creates/imports are drafts; approval needs a name; no-op save retains approval; content edit resets it; demo provenance survives edit/approval. |
| Archive | Archived questions cannot be edited/approved; restore is a draft; IDs remain reserved; conflicting prompt prevents restore. |
| Eligibility | Draft, archived and production-excluded demo records do not inflate availability. |
| Conflicts | Stale edits from a second connection cannot overwrite current data; duplicate edit leaves content/approval unchanged. |
| CSV syntax | UTF-8/BOM, Unicode, quoted commas, multiline text, MCQ mapping and reordered exact headers work. |
| CSV rejection | Wrong/duplicate/missing headers, bad column counts, malformed quotes, non-UTF-8, NUL, empty files, invalid marks/options and size/count limits block import. |
| Atomicity | Invalid rows block the entire batch; preview writes nothing; a simulated database failure on row 2 rolls back row 1. |
| Stale previews | ID collisions introduced after preview are caught before any insert; reimport is rejected. |
| Migration | v1 content/state preserved, v1 backup readable, revision initialized, reopen creates no extra backup; unsupported newer version unchanged. |

Source compilation, GUI imports, standalone sample availability, sample CSV preview and extraction/package checks are recorded with the release. Application code does not execute user-imported coding answers; only bundled authored fixtures are exercised by tests.

## Phase 3 automated evidence

- Demo generation has 13 unique IDs, 40 total marks, difficulty marks 12/20/8 and unit marks 18/22.
- All constraints hold over 100 seeds. The same seed repeats selection despite reversed input order; global random state is unchanged.
- Repeated groups across sections share a single candidate pool without reuse. Aggregate shortage reports the exact missing count.
- Production excludes all demo-origin records, drafts and archived questions; opted-in demo output is labelled.
- Invalid targets, fractional mark allocations, malformed approved questions and conflicting duplicate IDs are rejected.
- Independent postchecks reject changed question marks, IDs, row numbers, sections, counts, ordering, eligibility and summary totals.
- Student preview omits the answer/rubric/correct-option metadata included in the teacher key.
- Snapshots are independent of later mutations to input objects; generation performs no bank/paper writes.
- Saved templates preserve row order and multiline instructions across reopen; each save makes a new copy.
- Mid-save failure rolls back both header and rows; missing/corrupted templates are rejected.
- Existing schema-v2 bank data remains intact with no new migration.

Source compilation, GUI-module imports and command-line demo generation passed. No native window was rendered.

## Desktop acceptance checklist — not yet executed

This build environment has no display server, so native Tk windows were **not** launched or visually tested. HTML sketches are historical design references, not screenshots. Before demonstrating or submitting, test on the intended Windows laptop:

- [ ] Launch via `run_windows.bat`; all seven tabs render with no traceback.
- [ ] Add one Short answer, one Coding and one MCQ question; inspect multiline indentation and reload after restart.
- [ ] Submit empty required fields and invalid marks; errors are clear and typed entries remain.
- [ ] Switch question type and check MCQ controls/answers save correctly.
- [ ] Change an approved answer; confirm status returns to Draft.
- [ ] Cancel a dirty form or close the main app with it open; discard confirmation appears and Cancel keeps entries.
- [ ] Archive/restore, search and change filters; selection/status/counts stay understandable.
- [ ] Import valid and invalid examples in a fresh practice database; preview is readable, invalid import disabled, valid import requires confirmation.
- [ ] Repeat the import; duplicate errors appear and counts stay unchanged.
- [ ] Check 1366×768 and 125%/150% scaling, keyboard Tab/Shift+Tab/Escape, focus indicators, scrollbars and button reachability.
- [ ] Upgrade a copy of a Phase 1 database; inspect records and the timestamped backup.

## Ease-of-use and satisfaction acceptance targets — not measured

Observe two representative users completing add, approve, archive/restore, valid CSV import and invalid CSV recovery. Record elapsed time, independent completion, errors, help requests and a 1–5 ease/satisfaction score. Targets: both complete each task without developer intervention; no data loss; average ease and satisfaction at least 4/5. These are project targets, not claims of standardized usability certification. Fix blocking problems and repeat affected tasks. Keep a record in the final report.


## Phase 3 desktop checks — pending

- [ ] Enter metadata/targets/instructions; add/edit/remove and move rows, including the first/last row boundaries.
- [ ] Save a template, restart, reload it and compare all rows and instructions. Save an edited copy without changing the first copy.
- [ ] Load a demo or blank blueprint with unsaved edits; Cancel keeps the edits.
- [ ] With the bundled bank, production mode reports shortages. Demo mode produces 13 questions/40 marks and visible demo labels.
- [ ] Switch between student and teacher tabs; student question text has no answer/rubric/correct-option metadata.
- [ ] Type an invalid seed, invalid percentage or inconsistent marks; errors preserve inputs and block generation.
- [ ] Change setup/seed/mode or locally edit a bank record; stale preview and availability are cleared.
- [ ] Close with dirty row/editor/blueprint or a generated preview; declining the relevant discard dialog preserves work.
- [ ] Verify small-window layout, all buttons, scrollbars, Tab/Shift+Tab and 125%/150% Windows scaling.

The earlier user-satisfaction targets remain pending; no positive usability result is claimed.
