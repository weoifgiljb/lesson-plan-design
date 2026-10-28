# 变更日志

本文件记录每个发布标签的变更。版本号遵循语义化版本；标签打在 `main` 上，发布路径为 `feature/* → develop → main`，详见 [docs/dev/git-workflow.md](docs/dev/git-workflow.md)。

## 未发布

### 新增

- **平台端 UI v1.1「教案校样台」**：单一松绿主题、228px 标签式侧栏、56px 命令栏、自绘线性图标、命令面板、指标账本、审查队列与 DEV 概览预览（`/preview/overview`）。
- **three.js 教案结构剖面**：三维目标、八步流程与证据链的三层剖面；手写指针旋转、悬停说明、自动旋转/重置；无 WebGL、窄屏、chunk 失败或上下文丢失时降级为等距 SVG。仅在 DEV 预览挂载，生产包不含 `three`。
- **前端设计验收页 v1.1**：色彩与对比度、排版尺度、控件、数据展示、3D 规范、四态与响应式检查；截图脚本覆盖 1440/1280/390 与 2D 兜底，并断言 body 无横向溢出。

### 变更

- A「墨蓝」主题与 A/B 切换退役；`tokens.css` 只保留 `:root`，色板由 `styles/palette.ts` 与单测锁定。
- 登录页改为深松绿「书桌」分栏 + 纸面表单；共享组件（Table/Metric/Evidence/Diff/State/Chart）按新令牌重做。
- 生产构建仍只注册登录/403/404 与外壳；业务页面与真实 `/dashboard` 留待 FE-01…FE-09。

### 测试

- 前端 `npm run test`：9 个文件、27 条用例通过（含色板同步、对比度、结构模型、2D 兜底、指标格式化、命令过滤）。
- 前端 `npm run typecheck` / `npm run lint` / `npm run build` 通过；生产包无预览路由、演示数据与 three chunk。
- 仓库 `run_backend_gate.py`：block 0（架构 warn 2、契约 warn 1 为既有计划内项）。

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
