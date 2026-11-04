-- 0012：任务看板（四象限、排序、乐观锁版本、废弃标记）
BEGIN;

ALTER TABLE task ADD COLUMN quadrant TEXT NOT NULL DEFAULT 'important_not_urgent';
ALTER TABLE task ADD COLUMN board_position INTEGER NOT NULL DEFAULT 0;
ALTER TABLE task ADD COLUMN board_version INTEGER NOT NULL DEFAULT 0;
ALTER TABLE task ADD COLUMN discarded_at TEXT;

CREATE INDEX IF NOT EXISTS idx_task_board ON task (owner_id, quadrant, board_position);

COMMIT;
