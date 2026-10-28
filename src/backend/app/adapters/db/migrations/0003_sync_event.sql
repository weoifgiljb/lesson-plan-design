-- 0003：同步事件（删除也能被增量拉取）
--
-- `pull` 原先把 `plan_version.id` 当游标，软删除不产生新版本，客户端永远拉不到删除。
-- 这里引入单调递增的 sync_event：入库写 version 事件、软删除写 deleted 事件，
-- pull 改用事件 id 作游标，删除就能按同一游标传播。
CREATE TABLE IF NOT EXISTS sync_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('version', 'deleted')),
    plan_id INTEGER NOT NULL REFERENCES plan (id),
    plan_version_id INTEGER REFERENCES plan_version (id),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sync_event_plan ON sync_event (plan_id, id);
