# 0.6.1 rendering and input fixes

Date: 26 October 2026. **189 tests passed, zero skipped**, Python 3.12.3 / Tk 8.6 on Linux with a virtual X display and the existing PDF dependencies.

The previous 177 checks remain passing. Twelve new tests cover:

- Real Tk wheel dispatch over labels/page areas, Shift+wheel, nested text fields and tables without double scrolling, edge hand-off to the parent page, fractional Windows-style deltas, Linux button-wheel events, dropdown value preservation and later-created modal dialogs.
- Mocked Windows DPI APIs: modern context, respecting a configured host, older API fallback, missing API fallback and startup ordering before `Tk()`.

Rendered overview, bank, setup and paper previews at 96 and 144 DPI-equivalent Tk scaling. Checked larger font layout and the replacement ttk scrollbars. These renders do not prove Windows raster quality. The user's original whole-window quality concern has not been measured on their hardware. Windows system-DPI awareness targets bitmap scaling; mixed-DPI monitor transitions are not implemented as per-monitor-aware layout changes.

Manual Windows retest: fully close the previous Python process, launch 0.6.1, scroll over cards/labels/sidebar, scroll inside a question table and teacher key, use Shift+wheel on wide content, and inspect the entire window at the usual display scaling. Confirm dropdowns retain their values while scrolling. No OS-wide font, ClearType or display preferences are changed.

References for the Windows startup contract:

- https://learn.microsoft.com/en-us/windows/win32/hidpi/setting-the-default-dpi-awareness-for-a-process
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setprocessdpiawarenesscontext

---

# 0.6.0 GUI verification record

Date: 25 October 2026. Full suite: **177 tests passed, zero skipped**, Python 3.12.3 / Tk 8.6 on Linux with a virtual X display, ReportLab 4.4.9 and development dependencies. The existing 171 headless checks also passed on Python 3.12.14 before adding the display tests.

Six new real-widget tests (`tests/test_gui_workspace.py`) verify:

- Sidebar destinations, active states and database-backed dashboard counts, including exclusion of demo questions from the approved-for-exams count.
- Generation through the button, byte-for-byte preview text equality, section/demo tags, read-only saved states, revisions and cancelled opening over unsaved work.
- Question search, empty results, clearing filters, selection and complete answer details.
- Scrollable overflow on every workspace page at 960×680 and bringing generation controls into view.
- Question-editor content, cancellation and opening/closing the backup dialog without data changes.
- Enlarged text (Tk scaling 144/72): replacement Apply stays visible, marking guidance remains reachable, and CSV-import controls remain inside a 760×520 dialog.

Rendered and inspected the overview, question bank, paper setup, availability, student preview, teacher key, history and help. Also inspected the question editor, selection-row editor, backup and replacement dialogs at normal and enlarged text sizes. Fixed table-driven page overflow, theme-font overrides and clipped dialog controls found during these checks. Repository screenshots use only bundled demo data.

This is **Linux rendering and simulated Tk text scaling**, not a Windows DPI certification. Final manual checks remain: Windows 125%/150% scaling, keyboard focus through native dialogs, export/printing and restore/recovery with a disposable database. The user reported the previous Windows saving error resolved. No formal satisfaction or task-time measurements have been collected.

Run on a desktop:

```text
python -m unittest discover -s tests -v
```

On a Linux machine with Xvfb installed, `xvfb-run -a python -m unittest discover -s tests -v` supplies a display. Without a display, the real Tk class is explicitly skipped; existing headless tests still run. These are testing tools, not application requirements.

The records below describe earlier releases and retain their original test scope.

---

# Phase 5 verification record

Date: 25 October 2026. Runtime: Python 3.12.14. Platform: Linux build environment.

```text
python -m unittest discover -s tests -v
```

**Result: 171 tests passed (114 prior tests, 23 backup/restore tests, 18 PDF tests, 9 Phase 5 headless controller tests and 7 file-output regression tests).**

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


## Phase 4 desktop acceptance — main workflow confirmed by user

- [ ] Replace a question after comparing both dialog tabs. Check only that question changes and 13/40, difficulty and unit totals remain exact.
- [ ] Save, restart, reopen and compare both previews including code indentation.
- [ ] Create a revision, replace a question, save; original and revision reopen independently and show distinct IDs/parent linkage.
- [ ] Edit/archive a selected bank question; original saved student/key content stays unchanged.
- [ ] Open a replacement dialog, alter that candidate in a second app copy, then Apply: reject stale content and retain paper.
- [ ] Test no-alternatives explanation; Apply remains disabled.
- [ ] Decline discarding an unsaved paper/revision when opening/generating another or closing; work remains.
- [ ] Edit setup while a paper is open: Review stays unchanged; new generation uses the new setup.
- [ ] Verify history vertical/horizontal scrolling, keyboard selection, replacement dialog buttons and 125%/150% scaling.

The user reported that everything in Phase 4 was working on Windows. This confirms their functional workflow; the detailed edge-case/scaling checklist above and formal satisfaction measurements were not separately reported. Phase 5 now implements PDF export and backup/restore.


## Phase 5 automated and rendered verification

- Exact all-table backup/restore survives reopening, including question review/archive state, Unicode, blueprint rows, saved papers and revision parents.
- Recovery copies can reverse a successful restore. Copy failure or mid-insert failure rolls back changes, and database locks fail safely.
- Backup includes committed WAL content; new names protect older backups. Invalid versions/files, unexpected schema, corrupted paper JSON, bad hashes, orphan/gapped rows and missing revision parents are rejected.
- Cancelling preparation changes nothing. Restoring uses a private validated snapshot even if the selected source file changes after preview.
- Newly initialized databases seed demos; existing empty/restored databases remain empty, including CLI startup.
- PDFs contain correct student/teacher fields and metadata, all MCQ options, A4 pages, audience/demo labels and page numbers. Re-exporting a saved snapshot preserves printed text.
- Long code spans pages within bounds, code indentation has correct visual offsets, and markup-like user text remains literal.
- Missing ReportLab, unsupported scripts, invalid snapshots and file-output failures produce recoverable errors. Existing output and input data remain unchanged. Bundled-font fallback handles the English demo.
- Headless callbacks cover cancelled export/overwrite, unsaved-history status, invalid/cancelled/failed restore and app closure only after successful restore.

Rendered and visually inspected all pages of final demo outputs: **2 student pages and 4 teacher pages**. Checked margins, question/answer grouping, headings, code indentation, demo labels and footers. Long-code bounds are checked programmatically with pdfplumber. Development PDF dependencies are required; missing dependencies cause PDF tests to skip rather than implying verification.

Source compilation, GUI-module import and CLI smoke checks passed. No Phase 5 native window was rendered in the build environment.

## Phase 5 Windows acceptance — pending

- [ ] Install requirements with the same Python 3.12 interpreter used to launch the app.
- [ ] Export student and teacher PDFs from both a generated paper and a reopened saved revision; inspect every page and print A4 at 100%.
- [ ] Confirm student PDF has no answer/key metadata and teacher output has the correct answers/options.
- [ ] Cancel Save As/overwrite dialogs; existing file and open paper stay unchanged.
- [ ] Make a backup, reopen the dialog, inspect its record counts and cancel restore; no data changes.
- [ ] On a separate practice database, make a change after backup, restore, restart, then use the recovery copy to undo it.
- [ ] Confirm invalid backup input is rejected, and unsaved-work replacement warning is clear.
- [ ] Close other app instances before restore; confirm success closes the app and reports the recovery path.
- [ ] Check buttons, file dialogs, keyboard navigation and 125%/150% display scaling.

Formal completion-time/ease/satisfaction targets remain unmeasured. Complex-script PDFs, visual redesign and submission materials remain outside this implementation.


## 0.5.1 regression: Windows bad file descriptor

The user reported PDF export and backup failures on Windows with errno 9. The shared helper reopened its completed temporary file as `rb` before `os.fsync`. Python uses Windows `_commit`; the underlying buffer flush requires a writable handle. Reopening as `r+b` grants write access without truncating the completed PDF/database.

A regression guard performs a zero-byte write on the descriptor before the real fsync, enforcing write access without changing content. Before the fix, four tests reproduced errno 9 (plain publication, overwrite, PDF exports and backup/recovery). After the fix, all 171 tests pass. Genuine flush/publication failures still preserve prior files and clean up temporary files/reservations. Native Windows retest remains pending; no claim of a real Windows test run is made.

References:
- https://docs.python.org/3.12/library/os.html#os.fsync
- https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers
