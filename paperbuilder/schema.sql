PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY NOT NULL,
    subject TEXT NOT NULL CHECK(length(trim(subject)) > 0),
    unit TEXT NOT NULL CHECK(length(trim(unit)) > 0),
    topic TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL CHECK(kind IN ('MCQ','Short answer','Coding')),
    marks INTEGER NOT NULL CHECK(typeof(marks) = 'integer' AND marks > 0),
    difficulty TEXT NOT NULL CHECK(difficulty IN ('Easy','Medium','Hard')),
    prompt TEXT NOT NULL CHECK(length(trim(prompt)) > 0),
    answer TEXT NOT NULL CHECK(length(trim(answer)) > 0),
    rubric TEXT NOT NULL CHECK(length(trim(rubric)) > 0),
    options_json TEXT NOT NULL DEFAULT '[]',
    correct_option_id TEXT,
    review_status TEXT NOT NULL DEFAULT 'draft'
        CHECK(review_status IN ('draft','demo_reviewed','approved')),
    review_note TEXT NOT NULL DEFAULT '',
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0,1)),
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    prompt_hash TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(review_status != 'demo_reviewed' OR is_demo = 1)
);
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_prompt
    ON questions(subject, prompt_hash) WHERE active = 1;
CREATE INDEX IF NOT EXISTS question_selection
    ON questions(subject, unit, kind, marks, difficulty, active, review_status);

-- Reserved for the later editable blueprint workflow.
CREATE TABLE IF NOT EXISTS blueprints (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
    total_marks INTEGER NOT NULL CHECK(total_marks > 0),
    instructions TEXT NOT NULL DEFAULT '',
    targets_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS blueprint_rows (
    blueprint_id TEXT NOT NULL REFERENCES blueprints(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK(position > 0),
    section TEXT NOT NULL,
    unit TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('MCQ','Short answer','Coding')),
    marks INTEGER NOT NULL CHECK(marks > 0),
    difficulty TEXT NOT NULL CHECK(difficulty IN ('Easy','Medium','Hard')),
    question_count INTEGER NOT NULL CHECK(question_count > 0),
    PRIMARY KEY(blueprint_id, position)
);
-- Whole snapshot JSON is self-contained; never reconstruct an old paper from bank IDs.
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    app_version TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    is_demo INTEGER NOT NULL CHECK(is_demo IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER IF NOT EXISTS immutable_paper
    BEFORE UPDATE ON papers
    BEGIN SELECT RAISE(ABORT, 'Saved paper snapshots are immutable; create a revision.'); END;
PRAGMA user_version = 2;
