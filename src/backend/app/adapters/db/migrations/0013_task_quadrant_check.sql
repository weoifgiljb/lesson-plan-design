-- 0013：任务象限白名单约束
--
-- 0012 加 quadrant 列时只靠应用层 `task_rules.validate_quadrant` 校验，库层没有 CHECK。
-- 历史库/手工改库/未来迁移一旦写入白名单外的值，GET /tasks 与 /tasks/board 的响应模型
-- （TaskItem.quadrant 是 Literal 枚举）会直接 500，而不是给出可解释的错误。
--
-- SQLite 不能直接给已有表加 CHECK，按官方 12 步法重建表（与 0009 同法）；
-- 重建前先把白名单外的历史值归一成默认象限，避免迁移因 CHECK 失败。

PRAGMA foreign_keys = OFF;

BEGIN;

UPDATE task SET quadrant = 'important_not_urgent'
 WHERE quadrant NOT IN ('urgent_important', 'important_not_urgent',
                        'urgent_not_important', 'not_urgent_not_important');

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
    quadrant TEXT NOT NULL DEFAULT 'important_not_urgent'
        CHECK (quadrant IN ('urgent_important', 'important_not_urgent',
                            'urgent_not_important', 'not_urgent_not_important')),
    board_position INTEGER NOT NULL DEFAULT 0,
    board_version INTEGER NOT NULL DEFAULT 0,
    discarded_at TEXT,
    UNIQUE (course, week, session, class_name, title)
);

INSERT INTO task_new (id, course, week, session, title, class_name, owner_id, due_date,
                      status, created_at, assignee_id, group_name, term,
                      quadrant, board_position, board_version, discarded_at)
SELECT id, course, week, session, title, class_name, owner_id, due_date,
       status, created_at, assignee_id, group_name, term,
       quadrant, board_position, board_version, discarded_at
FROM task;

DROP TABLE task;

ALTER TABLE task_new RENAME TO task;

CREATE INDEX IF NOT EXISTS idx_task_assignee ON task (assignee_id, status);
CREATE INDEX IF NOT EXISTS idx_task_group ON task (group_name, status);
CREATE INDEX IF NOT EXISTS idx_task_identity
    ON task (course, week, session, class_name, title);
CREATE INDEX IF NOT EXISTS idx_task_board ON task (owner_id, quadrant, board_position);

COMMIT;

PRAGMA foreign_keys = ON;
