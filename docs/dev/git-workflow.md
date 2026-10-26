# 双端项目 Git 分支协作规范

> 适用范围：本仓库全部代码、需求、测试与论文材料。硬约束另见根目录 `AGENTS.md` 与 `.cursor/rules/git-workflow.mdc`；可执行技能见 `skills/git-workflow/SKILL.md`。

## 1 分支模型

```text
main                         发布分支，只接受来自 develop 的合并
└── develop                  集成分支，所有 feature 的回合目标
    ├── feature/fr-01-rules          插件端 FR-01
    ├── feature/fr-03-gate          插件端 FR-03
    ├── feature/fr-05-evidence      插件端 FR-05
    ├── feature/fr-07-mcp           插件端 FR-07
    ├── feature/fr-08-runtime       插件端 FR-08
    ├── feature/bs-01-ingest        平台端 BS-01
    ├── feature/bs-04-sync          平台端 BS-04
    ├── feature/bs-05-auth          平台端 BS-05
    ├── feature/bs-06-audit         平台端 BS-06
    └── test/integration            联调时创建，合并全部待发 feature
```

- `main`：可演示、可答辩的稳定版本；只通过 PR 接受 `develop` 的合并，不直接提交。
- `develop`：日常集成基线；只接受 feature 分支的 PR，不直接提交业务代码。
- `feature/<需求编号>-<slug>`：一个需求一个分支，从 `develop` 切出，完成后 PR 回 `develop`。
- `docs/*`：需求、测试、论文与规范文档；从 `develop` 切出，评审后回合 `develop`。
- `fix/<需求编号>-<slug>`：缺陷修复；从 `develop` 或 `test/integration` 切出，修复后回合原分支。
- `test/integration`：联调专用，从 `develop` 切出，合并全部待发 feature；联调通过后合回 `develop`，再进 `main`，随后可删除。

## 2 当前基线（2026-10-26）

| 分支 | 基点 | 说明 |
|---|---|---|
| `main` | `d6cd45b`（`v1.0.0`） | 发布分支；本轮由 `develop` 合入后打 `v1.1.0` |
| `develop` | v1.1.0 集成基线 | 已含后端评审闸门与文档目录迁移 |
| `docs/dual-end-specs` | 已合入 `develop` | 本轮需求、分工、测试用例与样例 |
| `feature/fr-01-rules` 等 9 条 | `develop` | 已建分支，等待开工 |
| `test/integration` | 联调时创建 | 不在开工阶段创建 |

说明：引导期（`develop` 从 `docs/dual-end-specs` 切出）已在 `v1.0.0` 发布时结束，`main` 与 `develop` 已恢复"main ← develop"的常规路径；此后每次发布由 `develop` 一次性合入 `main` 并打标签。

## 3 分支命名

| 类型 | 格式 | 示例 |
|---|---|---|
| 功能 | `feature/<id>-<slug>` | `feature/fr-01-rules`、`feature/bs-01-ingest` |
| 文档 | `docs/<slug>` | `docs/dual-end-specs` |
| 修复 | `fix/<id>-<slug>` | `fix/bs-04-conflict-409` |
| 联调 | `test/integration` | 固定名称，同一时间只保留一条 |
| 发布标签 | `v<主>.<次>.<修订>-<阶段>` | `v0.1.0-plugin-p0` |

`<id>` 用小写：插件端 `fr-01` 至 `fr-18`，平台端 `bs-01` 至 `bs-16`。一个分支只做一个需求；需求拆得过大时按验收点再切子分支，但回合目标仍是 `develop`。

## 4 生命周期

### 4.1 开工

```bash
git switch develop
git pull --ff-only origin develop
git switch -c feature/fr-01-rules
```

开工前确认：需求编号、验收标准、对应测试用例（TC-xx）三样齐全；缺任何一项先补文档，不写代码。

### 4.2 开发与提交

- 小步提交，一次提交只做一件事。
- 提交信息格式：`<type>(<id>): <摘要>`，`type` 取 `feat`、`fix`、`docs`、`test`、`refactor`、`chore`。
- 示例：`feat(FR-01): reject structured task without must-do`、`test(BS-01): add tampered package case`。
- 契约、schema、审查报告字段发生变化时，同一次提交必须带上黄金样例与回归用例。

### 4.3 PR 回合 develop

```bash
git push -u origin feature/fr-01-rules
# 在 GitHub 创建 PR，base=develop，标题带需求编号
```

PR 必须填写 `.github/pull_request_template.md`，至少包含：

1. 关联需求编号（FR/BS）与测试用例编号（TC）。
2. 变更说明与影响范围（插件端/平台端/契约）。
3. 本地已跑的命令与结果。
4. 未关闭问题与风险。

合并要求：CI/本地测试通过、至少一次自审记录、契约变更附黄金测试。单人项目由作者自审，导师按节点抽查。

### 4.4 联调

```bash
git switch develop
git switch -c test/integration
git merge --no-ff feature/fr-01-rules
git merge --no-ff feature/fr-03-gate
# ... 合并全部待发 feature
```

联调测试顺序：

1. 插件端单元与回归：`py -3 plugins/lesson-plan-design/skills/lesson-plan-design/test/index.py`。
2. 契约与样例：`py -3 tests/fixtures/dual-end/run_plugin_fixtures.py`，要求 12/12 全部通过。
3. 测试用例抽取：`py -3 scripts/extract_test_schema.py`。
4. 后端闸门：`py -3 scripts/run_backend_gate.py`，要求无 block；评审报告见 `.qa/reviews/`。
5. 平台端接口与端到端：执行 `docs/testing/测试用例_markmap.md` 第 6—12 章（平台端未实现前标"待实现"）。
6. 手工冒烟：按 TC 编号抽取 P0 用例执行。

联调中发现的缺陷：

- 属于某个 feature 的，回该 feature 分支修复，再合并到 `develop`，由 `develop` 合入 `test/integration`。
- 只在集成分支出现的，切 `fix/integration-<slug>`，修复后同时回 `test/integration` 与 `develop`。

### 4.5 发布

```bash
git switch develop
git merge --no-ff test/integration
git tag -a v0.1.0-plugin-p0 -m "插件端 P0 通过联调"
git push origin develop --tags
# 通过 PR 将 develop 合入 main
```

发布后删除 `test/integration`，保留标签与 PR 记录。`main` 只接受 `develop` 的 PR，不直接提交。

### 4.6 热修

线上或答辩前发现阻断问题：从 `main` 切 `fix/<id>-<slug>`，修复后同时回合 `main` 与 `develop`，并补一条回归用例。

## 5 测试门禁

| 阶段 | 必须通过 | 说明 |
|---|---|---|
| feature → develop | 该需求对应用例 + 插件端测试套件 | 失败不得合并 |
| feature → develop（平台端） | 该需求用例 + `py -3 scripts/run_backend_gate.py` 无 block + `py -3 scripts/run_all_tests.py` 全绿 | 另需 `skills/backend-review-gate` 出的独立评审报告，结论为通过/有条件通过 |
| develop → test/integration | 全量插件端用例 + fixtures 脚本 12/12 + 后端闸门 | 失败不得进入联调 |
| test/integration → develop | 全部 P0/P1 用例 + 契约包校验 + 冒烟 | 平台端实现后加接口与端到端 |
| develop → main | 联调报告 + 演示通过 + 导师确认 | 打标签后发布 |

平台端尚未实现时，平台端用例标记"待实现"，不得用"未执行"冒充通过。

## 6 冲突处理

- 两个 feature 改同一文件：先合并改动小的一侧，另一侧 rebase 到最新 `develop` 后解决冲突，禁止直接覆盖对方改动。
- 契约文件（schema、报告字段、manifest）冲突：以需求文档为准，双方同时更新黄金样例，冲突解决后必须重跑契约测试。
- 合并冲突不得用 `--ours`/`--theirs` 整体丢弃；逐个文件确认。

## 7 目录与提交边界

- 提交：源码、需求文档、测试用例与 schema、fixtures、构建与校验脚本、规范文件。
- 不提交：`node_modules/`、`output/`、`.dsh/`、`.codex_audio_tmp/`、个人临时文件、含学生信息的材料。
- 生成物（DOCX、schema）与源文件（MD、抽取脚本）同批提交，保证可复现。

## 8 常用命令

```bash
# 查看分支与跟踪关系
git branch -vv

# 从 develop 开新功能分支
git switch develop && git switch -c feature/bs-04-sync

# 合并 feature 到本地 develop（保持分支历史）
git switch develop && git merge --no-ff feature/bs-04-sync

# 查看将要合入 test/integration 的分支
git branch --no-merged develop

# 联调分支重建（确认无未合并提交后）
git branch -D test/integration
```

## 9 引导脚本

`scripts/git_branch_setup.ps1` 按本文档创建 `develop` 与 9 条 P0 feature 分支，可重复执行；已存在的分支会跳过，不覆盖、不删除。

```powershell
pwsh -File scripts/git_branch_setup.ps1 -DocsBranch docs/dual-end-specs
```
