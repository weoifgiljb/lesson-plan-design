-- 0007：任务归属与学期
--
-- 需求 BS-10 要求“教研组或教师创建教学任务”，并支持跨学期；
-- 组长建的任务要能被本组教师看到并推进，因此任务需要指派人与归属组。
ALTER TABLE task ADD COLUMN assignee_id INTEGER REFERENCES user (id);
ALTER TABLE task ADD COLUMN group_name TEXT NOT NULL DEFAULT '';
ALTER TABLE task ADD COLUMN term TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_task_assignee ON task (assignee_id, status);
CREATE INDEX IF NOT EXISTS idx_task_group ON task (group_name, status);
