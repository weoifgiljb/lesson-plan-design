-- 0002：幂等键落到数据库 + 放行记录归属到具体审查
--
-- 注意：plan_version 上有"不可更新"触发器，直接 UPDATE 回填会 ABORT；
-- 因此先临时移除触发器、回填、再原样重建。整篇用 BEGIN/COMMIT 包住，
-- 失败时整篇回滚（不会留下"加了列但没回填"的半成品库）。

BEGIN;

ALTER TABLE plan_version ADD COLUMN report_sha256 TEXT NOT NULL DEFAULT '';

DROP TRIGGER IF EXISTS plan_version_no_update;
DROP TRIGGER IF EXISTS plan_version_no_delete;

UPDATE plan_version
SET report_sha256 = COALESCE(
    (SELECT r.report_sha256 FROM review r WHERE r.plan_version_id = plan_version.id
     ORDER BY r.round LIMIT 1),
    ''
)
WHERE report_sha256 = '';

CREATE TRIGGER plan_version_no_update BEFORE UPDATE ON plan_version
BEGIN
    SELECT RAISE(ABORT, 'plan_version is immutable');
END;

CREATE TRIGGER plan_version_no_delete BEFORE DELETE ON plan_version
BEGIN
    SELECT RAISE(ABORT, 'plan_version is immutable');
END;

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

COMMIT;
