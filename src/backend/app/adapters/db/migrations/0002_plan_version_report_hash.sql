-- 0002：幂等键落到数据库 + 放行记录归属到具体审查
--
-- 1) plan_version 增加 report_sha256，并建 (plan_id, plan_hash, report_sha256) 唯一索引：
--    应用层"先查后插"之外，再由数据库兜底，避免并发下同一契约包产生两版。
-- 2) override 原表把 finding_id 设为全局 UNIQUE，不同教案的同名 finding 会静默丢放行记录；
--    重建为 (review_id, finding_id) 唯一，并补 review_id 归属。
--
-- 迁移只前进；版本号由 connection.initialize() 在脚本执行成功后推进。

ALTER TABLE plan_version ADD COLUMN report_sha256 TEXT NOT NULL DEFAULT '';

UPDATE plan_version
SET report_sha256 = COALESCE(
    (SELECT r.report_sha256 FROM review r WHERE r.plan_version_id = plan_version.id
     ORDER BY r.round LIMIT 1),
    ''
)
WHERE report_sha256 = '';

CREATE UNIQUE INDEX IF NOT EXISTS ux_plan_version_report
    ON plan_version (plan_id, plan_hash, report_sha256);

CREATE TABLE override_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES review (id),
    finding_id TEXT NOT NULL,
    teacher_id INTEGER REFERENCES user (id),
    reason TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    UNIQUE (review_id, finding_id)
);

INSERT INTO override_new (id, review_id, finding_id, teacher_id, reason, approved_at, plan_hash)
SELECT o.id,
       (SELECT MIN(r.id) FROM review r
          JOIN plan_version pv ON pv.id = r.plan_version_id
         WHERE pv.plan_hash = o.plan_hash),
       o.finding_id, o.teacher_id, o.reason, o.approved_at, o.plan_hash
FROM override o
WHERE EXISTS (
    SELECT 1 FROM review r JOIN plan_version pv ON pv.id = r.plan_version_id
     WHERE pv.plan_hash = o.plan_hash
);

DROP TABLE override;
ALTER TABLE override_new RENAME TO override;

CREATE INDEX IF NOT EXISTS idx_override_review ON override (review_id);
