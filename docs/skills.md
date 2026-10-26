# 开发与测试技能包（产品 + 测试 + 后端开发）

给本项目开发、自查、验收用的一套 Agent 技能。装好后直接说中文即可，不需要记命令。

- 安装位置：`.dsh/skills/`（本项目是 git 根，DSH 会自动发现该目录）
- 当前数量：**24 个技能**（5 个产品 + 13 个测试 + 6 个后端开发）
- 生效方式：本会话已热加载；新开会话、Cursor 重载后同样可见
- 来源：三个开源技能库，许可见[来源与许可](#来源与许可)
- 仓库内另有 `skills/code-standards`、`skills/git-workflow`、`skills/backend-review-gate` 三份**项目规范技能**：它们随仓库提交、供宿主与人工评审读取；本会话自动发现的只有 `.dsh/skills/`

---

## 一、产品经理技能（5）

| 你想做的事 | 技能 | 产出 |
|---|---|---|
| 写 / 改 PRD，把想法变成可开发的需求文档 | `create-prd` | 8 段式 PRD：摘要、背景、目标（SMART KR）、细分用户（JTBD）、价值主张、方案（P0/P1/P2）、发布计划 |
| 把需求写成用户故事，补验收标准 | `job-stories` | When / I want / So I can 故事 + INVEST 校验 + 6–8 条结果导向验收标准 |
| 需求太大，拆成能一周内交付的切片 | `story-splitting` | Richard Lawrence 9 种纵向切片模式 + 决策树 |
| 需求太多，排优先级 | `prioritization-frameworks` | RICE / ICE / MoSCoW / Kano 等 9 种方法 + 打分脚本 |
| 上线前做风险预演 | `pre-mortem` | 老虎 / 纸老虎 / 大象三类风险清单 + 处置建议 |

中文话术示例：

```text
用 create-prd 给「校标教案生成」写一份 PRD，目标用户是中职信息技术教师。
把这段需求拆成 job stories，每条给验收标准。
这三个需求用 RICE 排一下优先级，给出打分依据。
上线前帮我做一次 pre-mortem，列出可能翻车的点。
```

## 二、测试技能（13）

`qa` 是流水线入口，其余是单阶段技能。**只做一件事时直接用阶段技能**，不要每次都跑全流水线。

| 你想做的事 | 技能 |
|---|---|
| 「帮我完整测这个需求」——需求→策略→用例→评审→执行→Bug→回归→报告 | `qa` |
| 把 PRD/文档/代码梳理成需求模型，先列待确认问题 | `requirement-analysis` |
| 判断「这个功能该怎么测、哪些不测」 | `test-strategy` |
| 从 PRD / 接口文档 / 代码写可执行的手动用例 | `test-case-writing` |
| 审查已有用例的覆盖率和可执行性 | `test-case-review` |
| 用例转 Playwright E2E 并真跑 | `automated-e2e-testing` |
| 按 OpenAPI 测接口（参数、边界、鉴权、幂等、并发） | `api-testing` |
| 文档不全，先探索系统 | `exploratory-testing` |
| 已确认 Bug 的根因、影响面、回归建议 | `bug-analysis` |
| 代码改动后该回归哪些用例 | `regression-testing` |
| 用例时好时坏、重跑变绿能不能信 | `test-reliability` |
| 沉淀 / 读取本项目的测试经验 | `qa-memory` |
| 共享知识库（**不要单独调用**，其他测试技能依赖它） | `core` |

中文话术示例：

```text
用 qa 完整测一下「教案导出 Word」这个需求，先做需求分析和测试策略，有疑问先问我。
用 test-strategy 说一下这个功能怎么测、哪些不测。
根据这份 PRD 写测试用例，代码优先：先看代码找 bug 再写。
复查一下 tests/ 里这些用例的覆盖够不够。
这次改动（git diff）应该回归哪些用例？
```

## 三、后端开发技能（6）

给「不熟后端也要把平台端做对」准备的一组过程技能。它们不替你写代码，而是约束你怎么写、怎么写测试、怎么评审、怎么排错。

| 你想做的事 | 技能 | 产出 / 作用 |
|---|---|---|
| 把一句业务需求变成后端交接文档与风险清单 | `backend-api-brief` | 两份中文文档：给非技术读者看的接口说明 + 给开发看的后端交接（含权限、错误码、测试建议、待确认） |
| 让后端先写失败测试再写实现 | `test-driven-development` | 红-绿-重构循环；禁止先写实现后补测试 |
| 合并前发起一次独立评审 | `requesting-code-review` | 评审请求模板 + reviewer 关注点 + 证据要求 |
| 收到评审意见后逐条处理 | `receiving-code-review` | 防止"假修复"：先验证意见是否成立，再改，再复验 |
| 联调/测试失败时按假设—证据排查 | `systematic-debugging` | 复现、定位、加防御、防回归的固定顺序 |
| 声称"做完了"之前先拿证据 | `verification-before-completion` | 先跑命令、看输出、再下结论；禁止"应该可以了" |

中文话术示例（技能名是英文，说中文即可触发）：

```text
用 backend-api-brief 把「教案入库接口」这条需求写成后端交接，我拿给导师看。
按 test-driven-development 写入库复校，先给我失败的测试。
合并前跑一次 requesting-code-review，起独立评审，别自己审自己。
这个 500 错误按 systematic-debugging 查，先给复现步骤。
verification-before-completion：把这条命令的输出贴出来再告诉我通过。
```

**与项目闸门的关系**：这 6 个技能是通用方法；本项目的强制闸门是 `skills/backend-review-gate/SKILL.md` + `scripts/run_backend_gate.py`。方法技能服从闸门规则：`AGENTS.md` 与 `docs/backend-review-gate.md` 优先，技能里的"删掉重写""跳过测试"等建议不得越过本仓库门禁。

## 四、测试产出落在哪

- 流水线状态、用例、报告、Bug 条目：落在项目 `.qa/`，可断点续跑
- 后端评审报告：`.qa/reviews/backend-<分支>-<日期>.md`（同上，默认不进版本库）
- 注意：本仓库 `.gitignore` 目前忽略了 `/.qa/`，所以测试知识默认**不随 git 提交**
- 想让 `qa-memory` 的跨会话经验进版本库：删掉 `.gitignore` 里的 `/.qa/`，再按 `qa-memory` 的写入规范提交

## 五、脚本与运行环境

产品技能的脚本是纯标准库，无第三方依赖。**本机 `python` 是 Microsoft Store 的占位别名（退出码 9009），必须用 `py -3`。**

```powershell
# PRD 骨架（--objective / --segments 必填）
py -3 .dsh/skills/create-prd/scripts/prd_scaffolder.py `
  --product-name "校标教案生成平台" `
  --objective "把备课时间从 2 小时压到 20 分钟" `
  --segments "中职信息技术教师" `
  --output prd.md

# RICE 排序（--demo 看示例数据格式）
py -3 .dsh/skills/prioritization-frameworks/scripts/prioritization_scorer.py --demo --framework rice
py -3 .dsh/skills/prioritization-frameworks/scripts/prioritization_scorer.py --input items.json --framework rice

# 风险分类（pre-mortem 产出之后）
py -3 .dsh/skills/pre-mortem/scripts/risk_categorizer.py risks.json
```

测试技能的执行阶段需要另外装工具，**技能本身不代装**：

| 用途 | 需要 |
|---|---|
| Web E2E | Node + `npx playwright install` |
| API / 单测 | `py -3 -m pip install pytest requests` |
| 压测 | k6 |

后端开发技能是纯提示词（`systematic-debugging` 附带一个 Bash 脚本 `find-polluter.sh`，Windows 下可在 Git Bash/WSL 里用）；它们的执行依赖本仓库闸门：`py -3 scripts/run_backend_gate.py`、`py -3 scripts/run_all_tests.py`。

## 六、来源与许可

| 技能 | 来源仓库 | 版本 / 提交 | 许可 |
|---|---|---|---|
| 13 个测试技能 | [fishzjp/qa-skills](https://github.com/fishzjp/qa-skills) | v0.9.0 @ `f34e82d` | MIT |
| `create-prd`、`job-stories`、`story-splitting`、`prioritization-frameworks`、`pre-mortem` | [borghei/Claude-Skills · project-management](https://github.com/borghei/Claude-Skills/tree/main/project-management) | `2c12c7e` | MIT + Commons Clause |
| `requesting-code-review`、`receiving-code-review`、`test-driven-development`、`systematic-debugging`、`verification-before-completion` | [obra/superpowers](https://github.com/obra/superpowers) | v7.0.1 @ `2ce8aa1` | MIT |
| `backend-api-brief` | [datawhalechina/ai-skills-for-everyone](https://github.com/datawhalechina/ai-skills-for-everyone) | `247ffdf` | CC BY-NC-SA 4.0（内容；非商用毕设可用，需署名） |

`Commons Clause` 只限制「转售该软件」，个人/团队内部使用不受影响。除下列适配外，原始技能内容未改动，仅做目录扁平化（原路径记录在 `docs/skills.lock.json`）。

**接入适配（仅本地 `.dsh/skills/`，不入库）**

1. `backend-api-brief` 原文件 `description` 单行内含未转义的 `: `，YAML 解析失败、技能清单不出现；改为折叠块 `description: >`，正文未改。
2. `backend-api-brief` 默认把产物写到 `outputs/`；本仓库 `.gitignore` 不忽略该目录，使用时请改写到 `docs/api/` 或 `.qa/handoffs/`，避免误提交。
3. `obra/superpowers` 的技能面向通用项目，部分建议（删掉重写、先跳过测试）与本仓库门禁冲突，**以 `AGENTS.md` 与 `docs/backend-review-gate.md` 为准**。
4. 技能正文为英文，输出仍按你的语言。

## 七、升级与卸载

**升级**（重新拉取后覆盖，提交号以 `docs/skills.lock.json` 为准）：

```powershell
# 通用做法：下载固定提交的归档后覆盖对应目录
curl -L -o sp.tar.gz https://codeload.github.com/obra/superpowers/tar.gz/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b
tar -xzf sp.tar.gz
Copy-Item sp-*\skills\requesting-code-review .dsh\skills\ -Recurse -Force
# 其余技能同理：receiving-code-review / test-driven-development / systematic-debugging / verification-before-completion

curl -L -o dw.tar.gz https://codeload.github.com/datawhalechina/ai-skills-for-everyone/tar.gz/247ffdf08114c73c44c89aa56cc1eb0f65bc2271
tar -xzf dw.tar.gz
Copy-Item dw-*\skills\backend-api-brief .dsh\skills\ -Recurse -Force
# 覆盖后重新做上面的 front-matter 修正
```

`git clone` 在本机曾被网络中断；若 `curl` 也不通，用 Python 标准库下载同一归档：

```powershell
py -3 -c "import urllib.request; urllib.request.urlretrieve('https://codeload.github.com/obra/superpowers/tar.gz/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b', 'sp.tar.gz')"
```

13 个测试技能与 5 个产品技能的升级方式不变：

```powershell
git clone --depth 1 https://github.com/fishzjp/qa-skills.git tmp-qa
Copy-Item tmp-qa\skills\* .dsh\skills\ -Recurse -Force
Remove-Item tmp-qa -Recurse -Force
```

**卸载**：删掉 `.dsh/skills/` 下对应目录即可，本会话下一次心跳后目录会从技能清单消失。

**装成全局（所有项目可用）**：把同样的目录复制到 `~/.dsh/skills/`（该路径在沙箱工作区之外，需要授权），例如：

```powershell
Copy-Item .dsh\skills\* "$env:USERPROFILE\.dsh\skills\" -Recurse -Force
```

## 八、与既有 `lesson-plan-design` 的边界

- `lesson-plan-design`：业务技能，管「校标教案长什么样、怎么校验、怎么导出」
- 本技能包：过程技能，管「需求怎么写、优先级怎么排、怎么测、后端怎么审」
- 两者互不依赖。写教案时按原有流程，做需求、测试与后端评审时用本包。

## 九、已知限制

- 产品技能与后端开发技能正文是英文（`backend-api-brief` 是中文），输出仍按你的语言；命令示例里的 `python` 在 Windows 上换成 `py -3`
- 测试技能按宿主不同需要 Playwright / pytest，且要有可访问的测试环境和账号
- 技能是提示词与方法，不是 CI；要卡门禁仍得把 `validate.py`、`run_backend_gate.py`、pytest、Playwright 接进流程
- 后端闸门在后端开工前整组 skip（`ok=true, skipped=true`），这是预期行为，不是"已通过"
