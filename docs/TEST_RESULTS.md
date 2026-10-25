# Foundation verification record

Date: 22 October 2026. Runtime: Python 3.12.14. Platform: Linux execution environment.

Command from the project folder:

```text
python -m unittest discover -s tests -v
```

**Result: 16 tests passed.**

| Test area | Evidence |
|---|---|
| Sample schema | All 40 records pass question validation |
| Exact allocation | Demo blueprint is 13 questions and 40 marks; all six groups available |
| Demo isolation | Default production preflight excludes all demonstration questions |
| Safe seeding | Second seed adds zero records and preserves existing edits |
| Repeated groups | Demand aggregates across sections without inflating supply |
| Scarcity | Missing Module 1 Hard coding group produces exact shortage |
| Duplicate inputs | Repeated IDs in input do not inflate availability |
| Invalid targets | Negative, over-100, NaN, Infinity and nonnumeric percentages rejected |
| Incompatible marks | Fractional targets and mismatched row totals rejected |
| Invalid rows | Nonpositive, boolean, float and string marks rejected |
| MCQs | Invalid correct-option ID and repeated options rejected |
| Database integrity | Nonpositive marks and active exact-prompt duplicates rejected; foreign keys on |
| Snapshot schema | An UPDATE to a saved paper is rejected |
| Persistence | A second connection sees the same 40 records |
| Code text | Internal whitespace and case remain significant in duplicate hashes |
| Model code | Eight authored coding answers pass their trusted fixtures |

The demo preflight command (`python main.py --check`) succeeds. These results cover foundation functions, not generation, CSV import, export or end-user satisfaction.

## Manual checks still required on Windows

- Launch with the intended interpreter and verify all seven tabs render.
- Search/select questions and confirm code indentation remains readable.
- Test the valid blueprint, then 41 total marks and an invalid percentage sum.
- Check tab navigation, keyboard focus, 1366×768 resolution and 125%/150% scaling.
- Confirm app data persists after closing and reopening.

The GUI module was compiled and imported, but **no actual Tk window was displayed here**. Do not describe the HTML wireframes as tested GUI screenshots.
