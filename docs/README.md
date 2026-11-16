# 项目文档索引

「校标教案双端平台」毕业设计的全部文档都在本目录。仓库根目录只保留三个入口文件：

- [`README.md`](../README.md) —— 项目是什么、怎么用
- [`AGENTS.md`](../AGENTS.md) —— 协作与代码硬约束
- [`CHANGELOG.md`](../CHANGELOG.md) —— 发版记录

其余文档按用途分到下列子目录，**新文档不再直接放仓库根**。

## 目录总览

| 目录 | 放什么 | 主要读者 |
|---|---|---|
| [`requirements/`](requirements/) | 需求说明书、分工与协作说明（md + docx） | 导师、开发、测试 |
| [`testing/`](testing/) | 测试用例（markmap）、机器可读用例、样例教案 | 测试、开发 |
| [`dev/`](dev/) | Git 流程、代码规范与重构计划、技能包 | 全体 |
| [`backend/`](backend/) | B/S 端开发计划、后端评审闸门规范 | 后端、评审 |
| [`api/`](api/) | 双端契约 `contract.v1.json` | 前端、后端、测试 |
| [`thesis/`](thesis/) | 开题报告（两种口径）、论文提纲、配图 | 导师、作者 |
| [`setup/`](setup/) | 各宿主安装与接入配置 | 教师、部署 |

## 需求

| 文档 | 版本 | 状态 | 说明 |
|---|---|---|---|
| [功能优化需求-校标教案生成平台.md](requirements/功能优化需求-校标教案生成平台.md) | v1.7 | ✅ 18 / 🟡 0 / ⬜ 0 | 插件端 18 条可判定需求（FR-01—FR-18），含三态状态、证据与缺口 |
| [功能优化需求-BS平台端.md](requirements/功能优化需求-BS平台端.md) | v1.15 | ✅ 16 / 🟡 0 / ⬜ 0 | 平台端 16 条需求（BS-01—BS-16），含契约、错误码、验收口径与状态 |
| [跨端配置与数据恢复需求.md](requirements/跨端配置与数据恢复需求.md) | v1.4 | ✅ 8 / 🟡 0 / ⬜ 0 | 跨端配置与数据恢复 8 条需求（OPS-01—OPS-08），收敛 BS-14，含快照/恢复/防呆验收口径 |
| [界面风格优化需求.md](requirements/界面风格优化需求.md) | v1.4 | ✅ 1 / 🟡 6 / ⬜ 6 | 平台端视觉升级 13 条（UI-01—UI-13），与功能基线独立统计 |
| [界面风格优化需求.md](requirements/界面风格优化需求.md) | v1.4 | ✅ 1 / 🟡 6 / ⬜ 6 | 平台端视觉升级 13 条（UI-01—UI-13），与功能基线独立统计 |
| [需求分工与协作说明.md](requirements/需求分工与协作说明.md) | v1.0 | — | 角色、归属、交接与评审节点 |

同名 `.docx` 与 `.md` 并列存放，docx 是渲染产物，见[生成物与源文件](#生成物与源文件)。三态定义与证据基线见各需求文档第 0 节；下一批修复见[优化路线图](dev/优化路线图.md)。

## 测试

| 文档 | 说明 |
|---|---|
| [测试用例_markmap.md](testing/测试用例_markmap.md) | 12 个模块的 TC 用例；插件端以源码实测为证据，平台端已于 v1.2.0 实现，用例状态待逐条回填（见优化路线图） |
| [coverage.md](testing/coverage.md) | 核心模块覆盖率门禁：`py -3 scripts/coverage_gate.py`，当前 91.2% |
| [cross-host-smoke.md](testing/cross-host-smoke.md) | 5 个宿主安装冒烟清单与当前执行状态 |
| [测试用例.schema.yaml](testing/测试用例.schema.yaml) | 由 markmap 抽取的机器可读用例（生成物，勿手改） |
| [samples/教案-信息技术0102.json](testing/samples/教案-信息技术0102.json) | 用例引用的样例教案 |

## 开发规范

| 文档 | 说明 |
|---|---|
| [git-workflow.md](dev/git-workflow.md) | 分支模型、开工到发版的生命周期、合并门禁、冲突处理 |
| [优化路线图.md](dev/优化路线图.md) | 三态状态基线、已知缺口、批次与验收；下一步先做什么、为什么 |
| [代码规范与重构计划.md](dev/代码规范与重构计划.md) | 分层、映射、错误边界、路径卫生与重构排期 |
| [skills.md](dev/skills.md) | 24 个过程技能（产品 / 测试 / 后端）的清单、中文话术、来源许可与升级方式 |
| [skills.lock.json](dev/skills.lock.json) | 技能来源与提交号锁定（升级时以它为准） |

## 后端与契约

| 文档 | 说明 |
|---|---|
| [backend/bs-dev-plan.md](backend/bs-dev-plan.md) | B/S 端架构、接口清单、闸门与排期 |
| [backend/backend-review-gate.md](backend/backend-review-gate.md) | 8 组机器规则 + 独立评审流程；改 `src/backend`、`src/frontend/src/api`、`docs/api/` 前必读 |
| [api/contract.v1.json](api/contract.v1.json) | 教案 JSON、审查报告、manifest、`planHash` 与错误码的双端契约基线 |

## 论文

| 文档 | 说明 |
|---|---|
| [thesis/开题报告-校标教案双端平台.md](thesis/开题报告-校标教案双端平台.md) | 现行口径：插件端 + B/S 平台端 |
| [thesis/开题报告-校标教案生成平台.md](thesis/开题报告-校标教案生成平台.md) | 早期单端口径，保留用于对照需求基线 |
| [thesis/thesis-outline.md](thesis/thesis-outline.md) | 论文提纲 |
| [thesis/figures/](thesis/figures/) | 开题报告配图（流程图、架构图、校徽） |

## 环境安装

| 宿主 | 文档 |
|---|---|
| Cursor / Claude Code / Codex | [setup/ide-setup.md](setup/ide-setup.md) |
| Qoder | [setup/qoder-setup.md](setup/qoder-setup.md) |
| CodeBuddy | [setup/codebuddy-setup.md](setup/codebuddy-setup.md) |
| 飞书妙搭 / 豆包工作伙伴 | [setup/feishu-miaoda-setup.md](setup/feishu-miaoda-setup.md) |
| 换机/跨端迁移 | [setup/cross-device.md](setup/cross-device.md) |
| 每日自动备份 | [setup/auto-backup.md](setup/auto-backup.md) |

## 生成物与源文件

| 产物 | 源文件 | 重建命令 |
|---|---|---|
| `requirements/*.docx` | 同名 `.md` | `py -3 scripts/build_requirements_docx.py --src <需求.md> --out <同名.docx>` |
| `testing/测试用例.schema.yaml` | `testing/测试用例_markmap.md` | `py -3 scripts/extract_test_schema.py` |

构建脚本默认指向 FR 文档，其他需求文档用 `--src/--out` 指定；抽取脚本默认指向本目录。改完源文件重跑即可。**md 与 docx/schema 必须同批提交**，保证任何人 clone 后能复现。

## 维护约定

1. 新文档按用途放进上表某个子目录，不再放仓库根。
2. 一份文档只放一处；docx 与 md 同目录、同名。
3. 文档内引用其他文档用相对路径，禁止写本机绝对路径（`check_repo_hygiene.py` 会拦）。
4. 契约或需求版本变化时，同批更新 `api/contract.v1.json`、黄金样例与用例。
5. 文档改动走 `docs/*` 分支，PR 回合 `develop`，流程见 [dev/git-workflow.md](dev/git-workflow.md)。
6. 需求文档每条需求带 `✅ 已完成` / `🟡 部分完成` / `⬜ 未开始` 状态、证据与缺口；实现合入时同批更新，状态汇总同步本页与 [dev/优化路线图.md](dev/优化路线图.md)。
