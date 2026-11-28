CREATE TABLE IF NOT EXISTS deletion_request (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES plan (id),
    requester_id INTEGER NOT NULL REFERENCES user (id),
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    resolved_at TEXT,
    resolver_id INTEGER REFERENCES user (id)
);

CREATE INDEX IF NOT EXISTS idx_deletion_request_status
    ON deletion_request (status, created_at);
CREATE INDEX IF NOT EXISTS idx_deletion_request_plan
    ON deletion_request (plan_id, status);
