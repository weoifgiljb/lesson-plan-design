-- 0006：样例结构分与校验版本
--
-- 需求 BS-09 要求列表展示“结构分与有效性”，并要能追溯上传时用的是哪个规则/引擎版本。
ALTER TABLE sample ADD COLUMN score INTEGER NOT NULL DEFAULT 0;
ALTER TABLE sample ADD COLUMN engine_version TEXT NOT NULL DEFAULT '';
ALTER TABLE sample ADD COLUMN rule_version TEXT NOT NULL DEFAULT '';
