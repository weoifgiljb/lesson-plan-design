# 变更日志

本文件记录每个发布标签的变更。版本号遵循语义化版本；标签打在 `main` 上，发布路径为 `feature/* → develop → main`，详见 [docs/dev/git-workflow.md](docs/dev/git-workflow.md)。

## v1.2.0 — 2026-11-04

### 新增

- **B/S 平台端完整落地**（BS-01—BS-12）：契约包导入与入库复校、教案库与版本链、审查中心与证据链、双端同步与冲突处理、DOCX 导出中心、统计看板、样例库、任务四象限看板、账号会话与 JWT、审计与引擎设置；后端按 `domain / application / adapters / api` 分层，附带契约、OpenAPI 快照与前端生成类型。
- **前端业务页 FE-01—FE-08**：真实 `/dashboard` 概览、任务页、教案库/详情/正文、审查中心、导出中心、统计、样例库与管理页；平台端 UI v1.1「教案校样台」松绿主题、228px 标签侧栏、命令面板、自绘线性图标与四态/无障碍规范。
- **FE-06 统计页图表化重设计**：`/stats` 首屏三图——指标达成度（分子/分母与样本不足警示）、审查状态分布（环形 + 图例）、样本与可用性分段；交互包括点条形看口径、点扇区/图例看该状态教案、点样本分段在台账中定位并高亮；筛选、CSV 与下钻共用同一组参数；指标台账与下钻明细保留。
- **3D 教案结构剖面**：三维目标、八步流程、证据链三层，可悬停/点按；无 WebGL、窄屏、chunk 失败或上下文丢失时自动降级 2D；真实 `/dashboard` 懒加载 three chunk，固定演示数据只保留在 DEV `/styleguide`。
- **治理与文档**：后端评审闸门（架构/契约/安全/测试）与独立评审流程、契约类型化与前端类型生成、样例库与种子脚本；需求、测试、论文与规范文档按用途归档，根目录入口收敛到 `README.md`、`AGENTS.md`、`CHANGELOG.md`。

### 变更

- 统计口径统一为 9 项指标：分子/分母、样本不足（<5 份）、软删除不计、单份耗时回退口径；`/stats/records` 下钻返回课题标题，统计筛选、CSV 与下钻同口径。
- 任务唯一键纳入班级与课题；审查、导出、同步、统计的关键分支补后端回归、契约测试与独立评审。
- 平台端只保留单一浅色主题；统计页由「卡片 + 装饰性图表」改为「可读、可交互、可核对」的图表优先布局。

### 文档

- 《功能优化需求-BS平台端》升版（契约/接口/错误码与验收口径）；刷新后端开发计划、评审闸门、代码规范与难题索引。
- 开题报告、论文提纲与配图更新；`docs/README.md` 文档索引与迁移说明同步。

### 测试

- 前端：`npm run test` 33 files / 121 tests；`typecheck`、`lint`（0 error）、`build` 通过；`smoke-stats` 覆盖 1440/1280 首屏、图表交互、筛选/CSV/下钻与 loading/empty/error。
- 后端：`run_backend_gate.py` block 0 / warn 15 / 265 tests；`run_all_tests.py` 11/11 suites / 219 tests；`check_repo_hygiene.py` 通过。
- 已知限制：审查状态分布最多统计前 100 份（后续由后端 `statusCounts` 移除）；`stats_plans` 无 `ORDER BY` 的分页顺序与 `/stats/records` 跨组可见性测试列为后续 fix；ECharts 全量进入 `StatsView` chunk（约 1.07MB），后续按需注册；概览页「单份耗时」单位待修。

## v1.1.0 — 2026-10-26

### 新增

- **后端评审闸门**：`scripts/run_backend_gate.py` 与 8 组机器规则（`check_backend_architecture.py`、`check_backend_contract.py`、`check_backend_security.py`、`_gate_common.py`），配套 `tests/gate/` 自测与 `skills/backend-review-gate/` 独立评审流程。
- **B/S 端开发计划**：[docs/backend/bs-dev-plan.md](docs/backend/bs-dev-plan.md)，含前后端分层、接口清单、闸门与排期。
- **后端评审闸门规范**：[docs/backend/backend-review-gate.md](docs/backend/backend-review-gate.md)。
- **双端契约基线**：[docs/api/contract.v1.json](docs/api/contract.v1.json)，锁定 schema、rubric、rules 版本与错误码。
- **6 个后端开发技能**：后端需求交接、TDD、发起/接收评审、系统化排错、完成前验证；技能包合计 24 个，清单见 [docs/dev/skills.md](docs/dev/skills.md)。
- `tests/fixtures/dual-end/` 新增 zip-slip 攻击样例，契约包校验覆盖路径穿越。

### 变更

- 《功能优化需求-BS平台端》升至 v1.1（LPP-BS-001）：补契约、错误码与验收口径，需求文档与 docx 同批更新。
- `AGENTS.md`、`.cursor/rules/code-standards.mdc` 与 PR 模板加入后端分层（第 16 条）与后端闸门（第 17 条）约束。
- 测试临时目录改为沙箱安全写法，测试 runner 输出不再因 GBK 控制台抛 `UnicodeEncodeError`。

### 文档

- 全库文档按用途迁入 `docs/requirements`、`docs/testing`、`docs/dev`、`docs/backend`、`docs/thesis`、`docs/setup`、`docs/api`；仓库根目录只保留 `README.md`、`AGENTS.md`、`CHANGELOG.md`。
- 新增 [docs/README.md](docs/README.md) 文档索引，所有相对链接与脚本默认路径随迁。
- 开题报告两种口径（双端 / 单端）与配图统一归入 [docs/thesis/](docs/thesis/)。
- `.gitignore` 增加 `.dsh/`、`.codex_audio_tmp/` 与本地录音文件。

### 测试

- `py -3 scripts/run_all_tests.py`：11 个套件、212 个用例全部通过。
- `py -3 scripts/run_backend_gate.py`：无 block。
- 已知限制：B/S 平台端尚未实现，平台端用例在 [docs/testing/测试用例_markmap.md](docs/testing/测试用例_markmap.md) 中标注「待实现」，不计入通过。

## v1.0.0 — 2026-10-26

首个发布版本。插件端 `lesson-plan-design` 完成组件化重构（domain / application / adapters 分层，`lib.py`、`export_docx.py`、`mcp_server.py` 保留兼容入口）；双端需求、分工、测试用例与 fixtures 首次进仓；测试套件与双端样例脚本跑通。
