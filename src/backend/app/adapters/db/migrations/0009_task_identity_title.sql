-- 0009：任务唯一键加上课题
--
-- 原 UNIQUE(course, week, session, class_name) 把"同一班级在同一周次/课次只能有一个任务"
-- 写死了，导致同一班级换一个课题就被判成重复（CONFLICT_STALE）。一个班级在同一周次
-- 可以上不同课题的课，任务身份应是「课程 + 周次 + 课次 + 班级 + 课题」。
--
-- SQLite 不能直接改 UNIQUE 约束，按官方 12 步法重建表；重建期间关闭外键，
-- 避免 plan.task_id 的引用让 DROP TABLE 失败。

PRAGMA foreign_keys = OFF;

BEGIN;

CREATE TABLE task_new (
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
    assignee_id INTEGER REFERENCES user (id),
    group_name TEXT NOT NULL DEFAULT '',
    term TEXT NOT NULL DEFAULT '',
    UNIQUE (course, week, session, class_name, title)
);

INSERT INTO task_new (id, course, week, session, title, class_name, owner_id, due_date,
                      status, created_at, assignee_id, group_name, term)
SELECT id, course, week, session, title, class_name, owner_id, due_date,
       status, created_at, assignee_id, group_name, term
FROM task;

DROP TABLE task;

ALTER TABLE task_new RENAME TO task;

CREATE INDEX IF NOT EXISTS idx_task_assignee ON task (assignee_id, status);
CREATE INDEX IF NOT EXISTS idx_task_group ON task (group_name, status);
CREATE INDEX IF NOT EXISTS idx_task_identity
    ON task (course, week, session, class_name, title);

COMMIT;

PRAGMA foreign_keys = ON;
