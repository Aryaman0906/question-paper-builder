# Phase 4 verification record

Date: 25 October 2026. Runtime: Python 3.12.14. Platform: Linux build environment.

```text
python -m unittest discover -s tests -v
```

**Result: 114 tests passed (16 foundations, 31 Phase 2, 28 Phase 3, 29 Phase 4 service tests, 10 headless controller tests).**

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

## Phase 4 automated evidence

- Save/restart/reopen produces equal snapshots and identical student/teacher preview text.
- Bank edits, archives and missing bank records cannot change saved content.
- Repeated saves, including another connection, are idempotent; changed content under an existing ID is rejected.
- SQL update protection, injected insert failure and database lock recovery preserve data and permit retry.
- Missing/corrupt snapshots, invalid envelopes, duplicate JSON fields and metadata mismatch are rejected.
- Revisions have new IDs, retain parent IDs and preserve the original; sibling and nested revisions stay separate.
- Every demo slot has only exact matching, unused alternatives; replacing any slot preserves totals/order/uniqueness.
- Direct replacement of a saved paper is blocked. Revision replacement saves separately.
- Edited, archived or re-reviewed candidates after preview are rejected until refreshed.
- Production excludes demo, draft and archived alternatives. No alternatives never relaxes constraints.
- Headless controller tests verify unsaved paper preservation on bank/setup edits, cancelled open/generation/close, failed open/save/generation, and saved-versus-unsaved close behavior. These do not render widgets.

## User-confirmed Phase 3 Windows evidence — 25 October 2026

The user supplied screenshots of the running seven-tab application, then pasted matching student/key output for 13 unique questions and 40 marks (Easy 12, Medium 20, Hard 8; units 18/22). The user also confirmed a saved blueprint loaded after restarting. This establishes that workflow on their machine, not all controls or all edge cases. The downloaded batch launcher was blocked by Smart App Control; terminal launch with Python 3.12 was the instructed alternative.

## Desktop acceptance checklist — remaining checks

This build environment has no display server, so native Tk windows were **not** launched or visually tested. HTML sketches are historical design references, not screenshots. Before demonstrating or submitting, test on the intended Windows laptop:

- [x] Phase 3 launch and seven tabs rendered on the user’s Windows computer. Batch launcher remains subject to Smart App Control; terminal launch is documented.
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


## Phase 3 desktop checks — partially confirmed

- [ ] Enter metadata/targets/instructions; add/edit/remove and move rows, including the first/last row boundaries.
- [x] User confirmed saving and reloading a blueprint after restart.
- [ ] Compare every saved row/instruction and verify saving an edited copy preserves the first.
- [ ] Load a demo or blank blueprint with unsaved edits; Cancel keeps the edits.
- [x] User confirmed demo generation with 13 questions, 40 marks and expected balance.
- [ ] Confirm production mode reports shortages with a demo-only bank.
- [x] User pasted separate student/key previews; student text contains no teacher metadata.
- [ ] Type an invalid seed, invalid percentage or inconsistent marks; errors preserve inputs and block generation.
- [ ] Phase 4 behavior: setup/seed/mode/bank changes clear availability but preserve the independent paper in Review.
- [ ] Close with dirty row/editor/blueprint or a generated preview; declining the relevant discard dialog preserves work.
- [ ] Verify small-window layout, all buttons, scrollbars, Tab/Shift+Tab and 125%/150% Windows scaling.

The earlier user-satisfaction targets remain pending; no positive usability result is claimed.


## Phase 4 desktop acceptance — pending on Windows

- [ ] Replace a question after comparing both dialog tabs. Check only that question changes and 13/40, difficulty and unit totals remain exact.
- [ ] Save, restart, reopen and compare both previews including code indentation.
- [ ] Create a revision, replace a question, save; original and revision reopen independently and show distinct IDs/parent linkage.
- [ ] Edit/archive a selected bank question; original saved student/key content stays unchanged.
- [ ] Open a replacement dialog, alter that candidate in a second app copy, then Apply: reject stale content and retain paper.
- [ ] Test no-alternatives explanation; Apply remains disabled.
- [ ] Decline discarding an unsaved paper/revision when opening/generating another or closing; work remains.
- [ ] Edit setup while a paper is open: Review stays unchanged; new generation uses the new setup.
- [ ] Verify history vertical/horizontal scrolling, keyboard selection, replacement dialog buttons and 125%/150% scaling.

User satisfaction and Phase 4 visual acceptance have not been measured. PDF export/backup are not implemented yet.
