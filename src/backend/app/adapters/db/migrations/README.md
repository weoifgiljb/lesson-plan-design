# 数据库迁移

`schema.sql` 是 v1 全量结构，`app/adapters/db/connection.py` 在 `PRAGMA user_version = 0`
时执行它并把版本置 1。

后续结构变更按顺序新增文件，启动时由 `initialize()` 逐版执行：

```text
0002_add_xxx.sql
0003_add_yyy.sql
```

规则：

1. 迁移只追加，不改已发布的 `schema.sql`；
2. 迁移脚本内**不要**写 `PRAGMA user_version`：`initialize()` 在执行成功后统一推进 `SCHEMA_VERSION`；
3. 迁移前备份 `data/`（BS-14 会做成脚本）；
4. 迁移变更需同时更新 `docs/requirements/功能优化需求-BS平台端.md` 的数据模型表与契约测试；
5. 新增迁移时同步把 `connection.SCHEMA_VERSION` 加一，并补「v1 起步 → 升级到最新」用例。
