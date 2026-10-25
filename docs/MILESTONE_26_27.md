# Phase 3 — editable blueprints and generation

Scheduled objectives: 26–27 October 2026. Implemented: 25 October 2026. Student: Aryaman Kundra, roll 2445591.

## Checklist

- [x] Edit title, subject, duration, total marks, instructions and difficulty percentages.
- [x] Add, edit, remove and reorder exact selection rows.
- [x] Show live allocated marks and unit/difficulty totals.
- [x] Validate whole counts/marks and exact percentage targets; never silently round.
- [x] Save/load ordered blueprint copies atomically in SQLite.
- [x] Aggregate repeated groups across sections and report exact shortages.
- [x] Sample unique matching question IDs without replacement.
- [x] Offer explicit demo mode and optional repeatable seeds.
- [x] Independently validate the completed selection before displaying it.
- [x] Show separate student and teacher previews with marks/coverage summaries.
- [x] Invalidate local stale previews and warn on unsaved close/discard.
- [x] Add headless demo generation and 28 new automated tests (75 total).
- [ ] Verify native GUI layout and keyboard behavior on Windows.
- [ ] Measure ease of use and satisfaction with representative users.

## First demo

Run `py -3.12 main.py`. Open Paper setup and save the sample blueprint as a new template. On Availability, opt into Demo mode, choose Check blueprint and then Generate paper. The Review tab should show 13 unique questions and 40 marks: Easy 12, Medium 20, Hard 8. Module 1 has 18 marks and Module 2 has 22. Inspect the Student paper and Teacher key tabs.

To test without a window:

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 main.py --generate-demo --seed 42 --db .\practice.sqlite3
```

JSON output contains full teacher answers. It is not a student export.

## Decisions and limitations

The fixed-group model is exact: a row specifies one unit, one question type, one difficulty and one marks value. Identical groups share a pool, so two sections cannot consume the same question. Sampling is sufficient because different exact groups do not overlap. Future flexible alternatives or semantic duplicate constraints would need another algorithm.

Difficulty percentages apply to marks, not question counts. They reflect teacher-assigned labels, not measured student performance. Reproducible seeds require unchanged eligible content, blueprint and generator/runtime; different seeds do not guarantee distinct papers.

Saved templates persist after restart. Each save creates a new template copy to avoid overwriting another window's edits. Generated previews are temporary until the next phase implements saved-paper snapshots. PDF export, compatible replacement and general backup/restore remain pending. The entire project is not yet submission-complete.

## References checked for implementation

- Python 3.12 random: https://docs.python.org/3.12/library/random.html
- Python 3.12 SQLite: https://docs.python.org/3.12/library/sqlite3.html

These informed local RNG sampling and transactional persistence. No external question-bank content was copied.
