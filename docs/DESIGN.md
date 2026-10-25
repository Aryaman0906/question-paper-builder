# Foundations and implementation contracts

## Layers

`main.py` opens the dedicated demo database and GUI. `gui.py` contains presentation and navigation. `validation.py` contains pure rules; it has no Tkinter or database dependency. `storage.py` owns SQLite access. Later, add `generation.py`, `papers.py` and `pdf_export.py` without moving selection logic into widget callbacks.

## Database model

| Table | Key | Purpose | Implemented now |
|---|---|---|---|
| questions | id | Question content, labels, answer/rubric and review state | Schema, sample seeding and read service |
| blueprints | id | Exam metadata and difficulty targets | Schema reserved; editable/save service pending |
| blueprint_rows | blueprint_id, position | Ordered section and selection requirements | Schema reserved; sample JSON is used now |
| papers | id | Full immutable saved-paper snapshot | Schema/immutability trigger; save/reopen service pending |

`blueprint_rows.blueprint_id` references `blueprints.id` with cascading deletion. Foreign keys are explicitly enabled for each connection. Question selection uses an index on subject, unit, kind, marks, difficulty and status. A partial unique index rejects repeated prompt hashes among active questions in the same subject.

Question prompt hashing normalizes Unicode and line endings and strips only outer whitespace. Internal code indentation and case remain significant. This detects exact normalized copies, not paraphrases or all semantic duplicates.

### Question data dictionary

- `id`: stable string such as PY-001; never use table row order as identity.
- `subject`, `unit`, `topic`: syllabus classification. Topic is informational in this MVP.
- `kind`: MCQ, Short answer or Coding.
- `marks`: positive integer.
- `difficulty`: Easy, Medium or Hard, independent of question type.
- `prompt`, `answer`, `rubric`: nonempty text; multiline content is preserved.
- `options_json`: ordered option objects with stable IDs and text; empty for non-MCQs.
- `correct_option_id`: one valid MCQ option ID; null otherwise.
- `review_status`: draft, demo_reviewed or approved.
- `is_demo`, `active`: separate flags; demonstration review cannot masquerade as approval.
- `review_note`, `created_at`, `updated_at`, `prompt_hash`: review context and maintenance fields. Future edit services must update `updated_at` explicitly.

SQL constraints enforce basic scalar invariants; application validation enforces complete MCQs and cross-field rules. Future import/CRUD services must always call the same validator before writing.

### Snapshot contract for the later paper service

`snapshot_json` will contain `schema_version`, `paper_id`, exam metadata, instructions, ordered sections, the complete blueprint, ordered question snapshots (ID, text, marks, labels, options, answer, rubric), achieved difficulty/unit totals, generation time, app version and optional random seed. A snapshot must pass the independent validator before saving. Do not rebuild it from live question IDs or seed values. A changed saved paper becomes a new record/revision.

The snapshot JSON content contract is documented now; its serializer and full validation are scheduled for 28–29 October. The current trigger blocks updates but does not validate arbitrary JSON.

## Blueprint and eligibility rules

Each blueprint row has section, unit, kind, marks per question, difficulty and count. Subject is inherited from the blueprint. Selection key is `(subject, unit, kind, marks, difficulty)`; section is deliberately excluded, since the same candidates can be requested by different sections.

1. Validate required fields, positive integer counts/marks/duration and allowed labels.
2. Require row marks to equal total marks and difficulty targets to sum to exactly 100.
3. Convert percentages to marks using Decimal. Reject fractional mark targets; never round silently.
4. Sum counts across rows with the same selection key.
5. Count distinct eligible question IDs per group. Exclude inactive and draft questions. Default eligibility also excludes all demo content; the demo screen explicitly opts into demo-reviewed records.
6. Report required, available and shortfall counts per group.

With single-valued selection fields and aggregated identical groups, these groups are disjoint. Their counts prove availability for this fixed-group model. They do not prove a solution to future overlapping requirements.

## Planned generation procedure for 26–27 October

For each validated group, obtain approved candidates, use a local random-number generator to sample without replacement for the combined demand, then distribute those selected records among that group's ordered rows. Recompute every condition independently from the resulting paper. Generation is NOT implemented in 0.1.

Do not add lock/exclude families, flexible unit alternatives or semantic-duplicate groups to simple sampling without revisiting feasibility. Those create interacting constraints and may require backtracking or a solver. A time limit is not evidence of impossibility.

## Demonstration blueprint

| Section | Unit | Kind | Difficulty | Count × marks | Total |
|---|---|---|---|---|---|
| A | Module 1 | Short answer | Easy | 3 × 2 | 6 |
| A | Module 2 | Short answer | Easy | 3 × 2 | 6 |
| B | Module 1 | Short answer | Medium | 2 × 4 | 8 |
| B | Module 2 | Short answer | Medium | 3 × 4 | 12 |
| C | Module 1 | Coding | Hard | 1 × 4 | 4 |
| C | Module 2 | Coding | Hard | 1 × 4 | 4 |

13 questions, 40 marks. Difficulty marks 12/20/8 = 30/50/20%. Unit marks 18/22. Time is a configurable estimate, currently 60 minutes.

## References

- Python Tkinter: https://docs.python.org/3.12/library/tkinter.html
- Python ttk: https://docs.python.org/3.12/library/tkinter.ttk.html
- Python SQLite: https://docs.python.org/3.12/library/sqlite3.html
- SQLite foreign keys: https://www.sqlite.org/foreignkeys.html
- Python random: https://docs.python.org/3.12/library/random.html
- Exam blueprints: https://crlt.umich.edu/designing-effective-exams

The project checklist contains the broader assessment, accessibility and export references. Recommendations here are implementation decisions, not certifications or instructor-mandated rules.
