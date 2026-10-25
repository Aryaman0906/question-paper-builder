# Scope freeze for the first version

Decision date: 22 October 2026. Demonstration target: 5 November 2026.

## Objective

Let a teacher maintain a reviewed question bank and produce a paper that exactly meets a declared marks, unit, type and difficulty blueprint, then review, save and export it with a separate answer key.

## Chosen design

| Decision | First-version choice | Reason |
|---|---|---|
| User | One teacher on one computer | Avoid unrelated accounts and server work |
| Interface | Tkinter with ttk | Fits a Python desktop submission |
| Storage | Local SQLite | No server or internet required |
| Selection | Fixed, disjoint groups with sampling without replacement | Understandable and testable in a viva |
| Difficulty | Marks-weighted teacher labels | Explicit and inspectable; not a psychometric claim |
| Coverage | One subject and one unit per question | Avoid overlapping group ambiguity |
| Topics | Informational tags inside a unit | Fine-grained topic quotas are a later extension |
| Marks | Positive whole numbers | Avoid fractional rounding and unnecessary complexity |
| Choices | All questions compulsory | Attempted totals stay unambiguous |
| MCQs | Four distinct options, one correct stable option ID; no shuffle initially | Keep key mapping reliable |
| Output | A4 student PDF and separate teacher key | Meet practical classroom use |
| Historical papers | Immutable complete snapshots | Bank edits cannot rewrite an old paper |

## Included in the completed first version

Question CRUD and approval, archive/search/filter, validated CSV import, editable blueprint rows and templates, availability diagnostics, random selection, independent validation, compatible replacements, saved history, paper/key PDF export, backup/restore, help, setup guide and meaningful tests.

A complete GUI means these ordinary tasks are available through screens. It does not mean that every feature already works in version 0.1.

## Excluded until core requirements pass

Login/roles, cloud synchronization, student result collection, automated grading, OCR, AI question drafting, empirical difficulty calibration, multiple versions with cross-paper overlap limits, MCQ option shuffling, general OR/answer-any rules, DOCX export and question images.

## Acceptance criteria for the completed app

1. Every exported paper satisfies its exact blueprint; no duplicate question IDs or unresolved duplicate text.
2. Unavailable requirements produce actionable shortages; there is no silent relaxation.
3. The student file contains no answers or internal difficulty labels.
4. A saved paper remains the same after a bank edit and app restart.
5. A teacher can complete the create-to-export workflow without a terminal.
6. Observe users and report measured completion, time and ease scores. Do not invent satisfaction results.

## Assumptions to confirm during normal instructor review

The title does not prescribe an AI model, a fixed difficulty ratio or a particular GUI library. The chosen 30/50/20 example is adjustable. If the instructor requires a different structure, update the scope and fixtures explicitly. No claim of faculty approval is made for this plan or the sample bank.
