-- 0004：审计查询索引
--
-- 审计按时间范围、按对象（target_type + target_id）筛选；保留期 ≥1 年后表会变大，
-- 这两个索引避免全表扫描。
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log (created_at);
CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_log (target_type, target_id);
