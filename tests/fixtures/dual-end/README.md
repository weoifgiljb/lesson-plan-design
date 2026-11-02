# 双端测试样例

配套《测试用例_markmap.md》使用的可执行样例：插件端提供可直接校验的教案 JSON，平台端提供契约包与期望结果。平台端尚未实现，契约包用于 2027.03 联调后的入库用例。

## 目录

| 路径 | 内容 |
|---|---|
| `plugin/valid-0201.json` | 第 2 周第 1 次「一级考证辅导2」，结构合法 |
| `plugin/structured-task-missing-mustdo.json` | 结构化任务但缺「必须完成/必做」，目标：校验失败（FR-01） |
| `plugin/minutes-95.json` | 活动合计 95 分钟、计划学时 2，目标：校验失败（FR-01） |
| `plugin/bool-week.json` | 周次为布尔值，目标：校验失败（FR-01） |
| `plugin/missing-week.json` | 缺周次字段，目标：只报 1 条问题（FR-01） |
| `plugin/stale-plan.json` + `stale-plan.review.json` | 报告生成后教案被修改，目标：导出门禁拒绝（FR-05） |
| `platform/valid-package/` | 合法契约包源码：教案、审查报告、manifest、媒体 |
| `platform/tampered-title-package/` | 教案被篡改、manifest 保持原值 |
| `platform/bad-schema-package/` | manifest 与报告版本为 99 |
| `platform/media-hash-mismatch-package/` | manifest 中媒体哈希被改为全 0 |
| `platform/missing-media-package/` | manifest 引用媒体但文件缺失 |
| `platform/packages/*.zip` | 上述契约包打包结果，共 6 个，供上传用例直接使用 |
| `platform/packages/zip-slip.zip` | 含 `../evil.txt` 条目，由 `build_fixtures.py` 直接生成（无源码目录），目标：422 `PAYLOAD_REJECTED` |
| `expected.json` | 每个样例的目标结果（修复后应满足） |
| `build_fixtures.py` | 重新生成全部样例 |
| `run_plugin_fixtures.py` | 执行插件端用例并静态核验契约包 |

## 使用

在仓库根运行：

```bash
py -3 tests/fixtures/dual-end/build_fixtures.py
py -3 tests/fixtures/dual-end/run_plugin_fixtures.py
```

`run_plugin_fixtures.py` 退出码 1 表示存在未达标的验收项。当前基线（2026-10-26）**12 项全部通过**：插件端 5 项结构校验（FR-01 已合入）、1 项旧报告失效（FR-05）、平台端 6 个契约包的静态核验（合法包完整性、篡改检出、版本异常、媒体哈希不符、媒体缺失、zip 路径穿越）。

| 分组 | 项数 | 期望 |
|---|---|---|
| 插件端结构校验 | 5 | 合法包 `ok=true`；缺「必须完成」、95 分钟、布尔周次、缺周次均 `ok=false` |
| 旧报告失效 | 1 | 导出门禁拒绝，原因含"不匹配" |
| 平台端契约包 | 6 | 见 `expected.json`：201 / 422 + 错误码（含 `PAYLOAD_REJECTED`） |

平台端尚未实现，这 6 个包目前只做静态核验；入库接口实现后必须按 `expected.json` 逐条断言状态码与错误码。

## 契约包格式

```
manifest.json       契约版本、planHash、reportHash、schemaVersion、rubricVersion、files[]
plan.json           教案 JSON（本体不带版本字段）
plan.review.json    审查报告
media/page-003.png  可选媒体
```

`files[]` 记录每个文件的相对路径、SHA-256 与大小；平台端先验文件哈希，再独立重算 `planHash` 并重跑结构校验。zip 条目不得包含 `..`、绝对路径或符号链接，违反时返回 422 `PAYLOAD_REJECTED`。

## 注意

- 生成的文件不要手工修改；改样例请改 `build_fixtures.py` 后重新生成。
- `zip-slip.zip` 没有源码目录，直接由 `build_fixtures.py` 写入非法条目，重新生成后仍应存在。
- 平台端期望响应码与错误码见 `expected.json` 与《功能优化需求-BS平台端》v1.2 第 5.5 节。
- 样例中的学校、班级、教师均为测试数据，不含学生个人信息。
