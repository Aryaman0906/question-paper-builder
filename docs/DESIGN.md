# Implementation contracts — Phase 3

## Layers

`main.py` opens the local question database and GUI. `gui.py` contains presentation and navigation. `validation.py` contains pure rules; it has no Tkinter or database dependency. `storage.py` owns SQLite access, bank mutations and migrations. `question_bank.py` contains bank/editor/import widgets, and `csv_import.py` owns CSV parsing and preview. All GUI writes use repository services. `blueprint_gui.py` edits templates, `blueprints.py` persists new copies, and `generation.py` selects and independently validates papers. Later, add `papers.py` and `pdf_export.py` without moving selection logic into widget callbacks.

## Database model

| Table | Key | Purpose | Implemented now |
|---|---|---|---|
| questions | id | Question content, labels, answer/rubric and review state | Create/edit/approve/archive, validated atomic import, sample seeding and reads |
| blueprints | id | Exam metadata and difficulty targets | Validated save/load services; every save creates a new template |
| blueprint_rows | blueprint_id, position | Ordered section and selection requirements | Ordered row editing and atomic template persistence |
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
- `review_note`, `created_at`, `updated_at`, `prompt_hash`: review context and maintenance fields. Mutation services update `updated_at` and increment `revision` explicitly.

SQL constraints enforce basic scalar invariants; application validation enforces complete MCQs and cross-field rules. Import and bank mutation services call the same validator before writing.

### Snapshot contract for the later paper service

`snapshot_json` will contain `schema_version`, `paper_id`, exam metadata, instructions, ordered sections, the complete blueprint, ordered question snapshots (ID, text, marks, labels, options, answer, rubric), achieved difficulty/unit totals, generation time, app version and optional random seed. A snapshot must pass the independent validator before saving. Do not rebuild it from live question IDs or seed values. A changed saved paper becomes a new record/revision.

Phase 3 creates in-memory JSON-compatible snapshots with full selected questions and validates their selection constraints. The `papers` table save/reopen service remains scheduled for Phase 4. The existing SQL trigger does not validate arbitrary JSON.

## Blueprint and eligibility rules

Each blueprint row has section, unit, kind, marks per question, difficulty and count. Subject is inherited from the blueprint. Selection key is `(subject, unit, kind, marks, difficulty)`; section is deliberately excluded, since the same candidates can be requested by different sections.

1. Validate required fields, positive integer counts/marks/duration and allowed labels.
2. Require row marks to equal total marks and difficulty targets to sum to exactly 100.
3. Convert percentages to marks using Decimal. Reject fractional mark targets; never round silently.
4. Sum counts across rows with the same selection key.
5. Count distinct eligible question IDs per group. Exclude inactive and draft questions. Default eligibility also excludes all demo content; the demo screen explicitly opts into demo-reviewed records.
6. Report required, available and shortfall counts per group.

With single-valued selection fields and aggregated identical groups, these groups are disjoint. Their counts prove availability for this fixed-group model. They do not prove a solution to future overlapping requirements.

## Implemented generation procedure — Phase 3

For each validated group, obtain approved candidates, use a local random-number generator to sample without replacement for the combined demand, then distribute those selected records among that group's ordered rows. Recompute every condition independently from the resulting paper. This procedure is implemented in 0.3.0.

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


## Schema 2 migration and bank transactions

`questions.revision` is a positive integer starting at 1. Content/status changes increment it. Editor saves, approval and archive/restore require the displayed revision to match the current record. A stale operation fails without overwriting the newer record. No-op content saves preserve approval and revision.

A schema-v1 database is backed up with SQLite's backup API to a timestamped sibling before `ALTER TABLE` adds revision and advances `PRAGMA user_version` to 2 in a transaction. Unsupported future versions are refused. Close other app copies before upgrade; a migration backup is not a general backup/restore UI.

Every bank mutation runs under `BEGIN IMMEDIATE` and the connection transaction context. CSV imports snapshot the preview, repeat validation/duplicate checks under that lock and commit all rows together. Any exception rolls back the batch. New records cannot inject approval or demo origin. Archive retains IDs; restoring rechecks prompt uniqueness and sets Draft. Demo provenance remains immutable through the public bank API.

The application does not evaluate or execute question/answer text. Reviewer names are self-entered local notes, without authentication. Difficulty labels are human judgments. CSV file/row limits bound ordinary import work; semantic duplicate detection and empirical difficulty calibration remain outside this milestone.


## Phase 3 details

Saved blueprint IDs are UUIDs. Every save writes a new immutable template copy: header and ordered rows commit in one transaction. Loading reads both in one transaction and validates them before displaying. Old copies remain unchanged; delete/update services are outside this increment. No schema migration from version 2 is needed.

Generation copies inputs, deduplicates identical IDs (rejecting conflicting records), validates eligible content and aggregates demand by exact selection key. Sorted IDs and sorted keys make explicit-seed selection independent of bank iteration order. A local `random.Random` samples without replacement for each disjoint group; rows consume that group's selected sequence in blueprint order. Blank seed draws a fresh 63-bit seed, stored with the preview. A seed is for reproducibility, not exam security, and does not preserve a paper when the bank/runtime changes.

A separate validator recomputes question counts, IDs, row order, selection fields, eligibility, difficulty marks, unit totals and summary from the selected items. No partial paper is returned on failure. Student text uses an explicit selection of fields (prompt, options, marks and exam metadata); teacher text adds answers, rubrics, IDs and difficulty. Both have an explicit demo banner when demo mode was selected.

Changing local setup, mode, seed or bank content clears the temporary GUI preview. Cross-process changes are not live-subscribed; every generation takes a fresh bank read, and existing copied preview text remains unchanged. Saving templates does not save generated papers. JSON command output includes answers and must be treated as teacher data.
