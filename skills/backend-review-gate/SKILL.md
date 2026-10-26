---
name: backend-review-gate
description: >
  后端 PR 合并前的独立评审与闸门执行：跑 G0–G4 脚本、起独立 subagent 按清单评审、
  产出三档结论与可复验报告。用户说「审一下后端」「后端 review」「这个 PR 能不能合」
  「跑一下后端闸门」时使用；作者不熟后端时尤其适用。
---

# 后端评审闸门

规范全文见 `docs/backend-review-gate.md`；开发计划见 `docs/bs-dev-plan.md`；硬约束见 `AGENTS.md` 第 16–17 条。

## 何时使用

- 任何改动 `src/backend`、`src/frontend/src/api`、`docs/api/` 的 PR 合并前；
- 新增/修改接口、错误码、数据库表、上传解析、会话与权限；
- 作者（学生）自己写的后端代码要进入 `develop` 之前——**你必须做那个不信任的评审者**。

不适用：纯文案、纯样式、纯插件端改动。

## 铁律

1. **不自己审自己**：评审必须起一个独立 subagent（或独立会话），把 diff 与证据交给它；不要在同一上下文里"再看一遍"。
2. **先证据后结论**：没跑 `run_backend_gate.py` 与 `run_all_tests.py` 就不许写"通过"。
3. **测试不许迁就实现**：发现改了测试期望、删了断言、只测 mock，直接判"拒绝"。
4. **安全和契约不允许例外**：BSEC-*、BC-* 任一 block，结论只能是"拒绝"。
5. **报告可复验**：每条 finding 必须给复验命令，复查时按命令重跑，不接受"我已经改好了"。

## 流程

### 1 收集证据

```bash
git switch <分支>
git diff develop...HEAD --stat
git diff develop...HEAD -- src/backend src/frontend/src/api docs/api
py -3 scripts/run_backend_gate.py --json
py -3 scripts/run_all_tests.py
py -3 scripts/check_repo_hygiene.py
```

把以下材料整理成一段文本交给评审 subagent：diff、闸门 JSON、`docs/api/contract.v1.json`、关联的 BS 编号与 TC 编号、本次 PR 声称完成的内容。

### 2 起独立评审

用 `subagent` 工具，提示词至少包含：

```text
你是独立后端评审者，只依据下面的 diff、闸门输出与契约评审，不要相信作者结论。
项目：校标教案双端平台（FastAPI + SQLite + Vue3）。
规范：docs/backend-review-gate.md 的 8 组清单与判定规则。
输出：每条 finding 含 文件:行 / 证据 / 严重度(blocker|major|minor) / 修复建议 / 复验命令；
      最后给三档结论（通过 / 有条件通过 / 拒绝），并写「给非后端读者的三句话结论」。
<贴 diff、闸门 JSON、契约、BS/TC 编号>
```

### 3 按 8 组清单判定

| 组 | 必查项 | 常见问题 |
|---|---|---|
| 身份与归属 | 读接口是否按 owner/组过滤；401 与 403 是否区分；改 URL id 能否越权 | 只在列表页过滤，详情页漏过滤 |
| 契约与哈希 | 是否独立重算 planHash；是否采信 manifest 自述；未知版本是否拒收 | 直接信 `manifest.planHash` |
| 幂等与事务 | 重复提交是否只产生一版；落库与审计是否同事务；冲突是否 409 不自动合并 | 先落库后审计，失败留下脏数据 |
| 输入与文件 | zip 条目白名单；大小上限；路径规范化；媒体哈希；MIME/类型 | `extractall`、`root / user_input` |
| 数据与不可变 | 触发器是否存在；软删除是否物理删；审计有无改删接口 | 应用层"约定不改"但库里能改 |
| 错误码与日志 | 响应是否泄露堆栈与路径；traceId 能否串日志；日志是否含教案全文 | `logger.info(plan)` |
| 依赖与配置 | 版本是否锁定；有无绝对路径；离线能否安装；engineVersion 是否记录 | 直接 `pip install` 最新版 |
| 测试诚实性 | 是否先红后绿；断言是否对准真实行为；边界与错误用例是否覆盖 | 把期望值改成实际值让测试变绿 |

### 4 三档结论

- **通过**：G0–G4 全绿，无 blocker/major。
- **有条件通过**：只剩 minor 或 warn，逐条列复查项与期限（不晚于下一个节点评审）。
- **拒绝**：任一 block、黄金 fixtures 红、权限矩阵缺项、测试迁就实现。

### 5 报告落盘

写到 `.qa/reviews/backend-<分支>-<日期>.md`（`.qa/` 已 gitignore，不进版本库），结构：

```markdown
# 后端评审报告 <分支> <日期>

## 给非后端读者的三句话结论
1. ……
2. ……
3. ……

## 结论
通过 / 有条件通过 / 拒绝

## 闸门证据
- run_backend_gate --json：block 0，warn 2，tests 41
- run_all_tests：11/11

## Findings
| # | 严重度 | 位置 | 证据 | 修复建议 | 复验命令 |
|---|---|---|---|---|---|

## 有条件通过项
| 项 | 期限 | 复查方式 |
|---|---|---|

## 未关闭风险
```

同时把「结论 + 3 条要点 + 报告路径」填进 PR 模板的后端评审段。

### 6 复查

修复后按同一清单与同一复验命令重跑；结论要写"第 N 轮复查"。**复查不通过就再拒绝，不许放行。**

## 与外部技能配合

- 需要发起独立评审批次时用 `requesting-code-review`；收到意见后按 `receiving-code-review` 逐条处理。
- 后端实现阶段用 `test-driven-development`（先红后绿）与 `verification-before-completion`（先跑命令再声称完成）。
- 联调排错用 `systematic-debugging`。
- 与仓库规范冲突时，以 `AGENTS.md` 与 `docs/backend-review-gate.md` 为准。

## 中文话术

```text
审一下 feature/bs-01-ingest 的后端，跑闸门并起独立评审，给三档结论。
这个后端 PR 能不能合？先跑 run_backend_gate，再按 8 组清单挑问题。
复查上一轮的 blocker，逐条给复验命令。
```
