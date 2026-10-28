-- 0005：导出任务记录报告哈希 + 并发唯一约束
--
-- 导出复用键改成 (plan_version_id, engine_version, report_sha256)：同一版本但报告换了，
-- 必须重新导出，不能复用旧 DOCX。唯一索引保证并发下不会写出两份 succeeded。
ALTER TABLE export_job ADD COLUMN report_sha256 TEXT NOT NULL DEFAULT '';

CREATE UNIQUE INDEX IF NOT EXISTS ux_export_job_succeeded
    ON export_job (plan_version_id, engine_version, report_sha256) WHERE status = 'succeeded';
