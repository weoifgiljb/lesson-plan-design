# 仓库协作硬约束（常驻）

适用范围：本仓库全部代码、需求、测试与论文材料。完整流程见 `docs/git-workflow.md`，可执行技能见 `skills/git-workflow/SKILL.md`。

1. **main 只发布**：`main` 只接受来自 `develop` 的 PR，禁止直接提交；发布必须打标签。
2. **develop 只集成**：`develop` 只接受 `feature/*`、`docs/*`、`fix/*` 的 PR，禁止直接提交业务代码。
3. **一需求一分支**：每个需求从 `develop` 切 `feature/<id>-<slug>`（如 `feature/fr-01-rules`），完成并自测后 PR 回合 `develop`；禁止一个分支混做多个需求。
4. **文档与测试走 docs/test**：需求、分工、测试用例与 fixtures 放 `docs/*` 或 `test/*` 分支，评审后回合 `develop`。
5. **联调单独建分支**：联调时从 `develop` 切 `test/integration`，合并全部待发 feature，跑全量测试；通过后回合 `develop`，再经 PR 进 `main`，随后删除联调分支。
6. **提交信息**：`<type>(<id>): <摘要>`，`type` 取 `feat`、`fix`、`docs`、`test`、`refactor`、`chore`；一次提交只做一件事，并写明关联的 FR/BS 与 TC 编号。
7. **合并门禁**：feature 至少跑通本需求用例与插件端测试套件；进入联调前，`tests/fixtures/dual-end/run_plugin_fixtures.py` 必须全部通过（FR-01 未合入前的 4 项基线失败视为已知，不得带入联调）。
8. **契约变更同批提交**：教案 JSON、审查报告、manifest、`planHash` 或错误码变化时，必须同时更新黄金样例、契约测试与需求文档；未知版本一律拒收。
9. **冲突不整体丢弃**：解决合并冲突时逐个文件确认，禁止用 `--ours`/`--theirs` 覆盖对方改动。
10. **不提交**：`node_modules/`、`output/`、`.dsh/`、`.codex_audio_tmp/`、个人临时文件与含学生信息的材料；生成物与源文件同批提交，保证可复现。

## 代码组织硬约束

完整规范见 `skills/code-standards/SKILL.md` 与 `docs/代码规范与重构计划.md`。

11. **路径**：已跟踪文件不写本机绝对路径；用 `${PLUGIN_ROOT}`、`Path(__file__).resolve().parents[n]` 或 `<仓库根目录>` 占位。
12. **映射**：类型、状态、错误码、severity 等封闭集合用常量表/映射，不写长 `if` 链。
13. **分层**：domain（模型/校验/评分/审查/门禁）不 import CLI/MCP/DOCX；adapters 只做协议适配。
14. **单一边界**：业务函数只抛异常；CLI/MCP 各保留一个错误适配层；审查状态只由 `derive_review_status(findings)` 推导。
15. **拆分纪律**：先补测试再搬代码，保留 `lib.py`/`export_docx.py`/`mcp_server.py` 兼容入口；单函数建议 ≤50 行、单模块建议 ≤400 行，超出在 PR 说明。

## 当前分支基线（2026-10-26）

- `main`：`9bc7fbb`（发布分支）
- `docs/dual-end-specs`：本轮需求、分工、测试用例与样例
- `develop`：从 `docs/dual-end-specs` 切出，后续集成基线
- P0 feature 分支：`feature/fr-01-rules`、`feature/fr-03-gate`、`feature/fr-05-evidence`、`feature/fr-07-mcp`、`feature/fr-08-runtime`、`feature/bs-01-ingest`、`feature/bs-04-sync`、`feature/bs-05-auth`、`feature/bs-06-audit`
- `test/integration`：联调时创建，不在开工阶段创建

发布路径：`feature/* → develop → test/integration → develop → main`。
