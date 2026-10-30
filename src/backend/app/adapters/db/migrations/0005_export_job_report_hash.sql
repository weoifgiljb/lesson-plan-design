-- 0005：导出任务记录报告哈希 + 并发唯一约束
--
-- 导出复用键改成 (plan_version_id, engine_version, report_sha256)：同一版本但报告换了，
-- 必须重新导出，不能复用旧 DOCX。唯一索引保证并发下不会写出两份 succeeded。
--
-- 整篇用 BEGIN/COMMIT 包住：早期版本没有事务，建唯一索引失败时会留下"列已加、版本没推进"
-- 的半成品库，之后每次启动都报 duplicate column（R3-1）。重复的 succeeded 记录先保留
-- 最新一条、其余标 failed，避免老库在升级时直接失败（R3-2）。

BEGIN;

ALTER TABLE export_job ADD COLUMN report_sha256 TEXT NOT NULL DEFAULT '';

UPDATE export_job
SET status = 'failed'
WHERE status = 'succeeded'
  AND id NOT IN (
      SELECT MAX(id) FROM export_job WHERE status = 'succeeded'
      GROUP BY plan_version_id, engine_version, report_sha256
  );

CREATE UNIQUE INDEX IF NOT EXISTS ux_export_job_succeeded
    ON export_job (plan_version_id, engine_version, report_sha256) WHERE status = 'succeeded';

COMMIT;
