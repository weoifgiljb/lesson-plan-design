-- 0011：用户令牌版本（改密/重置后自增，旧 JWT 立即失效）
BEGIN;

ALTER TABLE user ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1;

COMMIT;
