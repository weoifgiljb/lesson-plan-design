PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('teacher', 'lead', 'admin')),
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
    failed_count INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES user (id),
    token_hash TEXT NOT NULL UNIQUE,
    csrf_token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course TEXT NOT NULL,
    week INTEGER NOT NULL,
    session INTEGER NOT NULL,
    title TEXT NOT NULL,
    class_name TEXT NOT NULL DEFAULT '',
    owner_id INTEGER NOT NULL REFERENCES user (id),
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'reviewing', 'passed', 'exported')),
    created_at TEXT NOT NULL,
    UNIQUE (course, week, session, class_name)
);

CREATE TABLE IF NOT EXISTS plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES task (id),
    owner_id INTEGER NOT NULL REFERENCES user (id),
    current_version_id INTEGER,
    content_title TEXT NOT NULL,
    week INTEGER NOT NULL,
    session INTEGER NOT NULL,
    course TEXT NOT NULL DEFAULT '',
    deleted_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES plan (id),
    version_no INTEGER NOT NULL,
    content_json TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    rubric_version TEXT NOT NULL,
    engine_version TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'import',
    created_at TEXT NOT NULL,
    UNIQUE (plan_id, version_no)
);

CREATE TABLE IF NOT EXISTS review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_version_id INTEGER NOT NULL REFERENCES plan_version (id),
    round INTEGER NOT NULL,
    report_json TEXT NOT NULL,
    report_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    reviewer_mode TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (plan_version_id, round)
);

CREATE TABLE IF NOT EXISTS finding (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES review (id),
    finding_id TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('blocker', 'major', 'minor')),
    status TEXT NOT NULL CHECK (status IN ('open', 'waived', 'accepted')),
    hypothesis TEXT NOT NULL DEFAULT '',
    UNIQUE (review_id, finding_id)
);

CREATE TABLE IF NOT EXISTS override (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id TEXT NOT NULL UNIQUE,
    teacher_id INTEGER REFERENCES user (id),
    reason TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    plan_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS export_job (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_version_id INTEGER NOT NULL REFERENCES plan_version (id),
    engine_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    docx_path TEXT,
    docx_sha256 TEXT,
    operator_id INTEGER NOT NULL REFERENCES user (id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sample (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course TEXT NOT NULL,
    week INTEGER NOT NULL,
    session INTEGER NOT NULL,
    title TEXT NOT NULL,
    json_path TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    valid INTEGER NOT NULL DEFAULT 1 CHECK (valid IN (0, 1)),
    UNIQUE (course, week, session, title)
);

CREATE TABLE IF NOT EXISTS asset (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    caption TEXT NOT NULL DEFAULT '',
    attach_to TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,
    package_sha256 TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    result TEXT NOT NULL,
    conflict_code TEXT NOT NULL DEFAULT '',
    operator_id INTEGER REFERENCES user (id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER REFERENCES user (id),
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL DEFAULT '',
    before_hash TEXT NOT NULL DEFAULT '',
    after_hash TEXT NOT NULL DEFAULT '',
    detail_json TEXT NOT NULL DEFAULT '{}',
    ip TEXT NOT NULL DEFAULT '',
    trace_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_plan_owner ON plan (owner_id, deleted_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_plan_identity
    ON plan (owner_id, course, week, session, content_title) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_plan_version_plan ON plan_version (plan_id, version_no);
CREATE INDEX IF NOT EXISTS idx_plan_version_hash ON plan_version (plan_hash);
CREATE INDEX IF NOT EXISTS idx_review_version ON review (plan_version_id, round);
CREATE INDEX IF NOT EXISTS idx_finding_review ON finding (review_id);
CREATE INDEX IF NOT EXISTS idx_session_user ON user_session (user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log (actor_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log (action, created_at);
CREATE INDEX IF NOT EXISTS idx_sync_log_plan ON sync_log (plan_hash, created_at);

CREATE TRIGGER IF NOT EXISTS plan_version_no_update BEFORE UPDATE ON plan_version
BEGIN
    SELECT RAISE(ABORT, 'plan_version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS plan_version_no_delete BEFORE DELETE ON plan_version
BEGIN
    SELECT RAISE(ABORT, 'plan_version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS audit_log_no_update BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;

CREATE TRIGGER IF NOT EXISTS audit_log_no_delete BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;

CREATE TRIGGER IF NOT EXISTS sync_log_no_update BEFORE UPDATE ON sync_log
BEGIN
    SELECT RAISE(ABORT, 'sync_log is append-only');
END;

CREATE TRIGGER IF NOT EXISTS sync_log_no_delete BEFORE DELETE ON sync_log
BEGIN
    SELECT RAISE(ABORT, 'sync_log is append-only');
END;
