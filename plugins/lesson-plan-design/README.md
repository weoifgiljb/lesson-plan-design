# 校标教案设计 Plugin

给东莞经贸学校信息技术课写教案用。你用自然语言提需求，Agent 按技能 `lesson-plan-design` 生成**校标结构**（元信息、三维目标、八步流程），校验通过后再导出 Word。

飞书豆包工作伙伴只需拖入 `skills/lesson-plan-design/`；Cursor / Claude Code / Codex 安装整个插件目录。

---

## 技能怎么用

### 1. 你要提供什么

| 必给 | 说明 | 例子 |
|------|------|------|
| 周次 | 正整数 | 第 2 周 |
| 课次 | 正整数 | 第 1 次课 |
| 教学内容标题 | 课题 | 一级考证辅导2 |

可选：练习套别、班级、教师、日期、学时。不说则用默认校标（东莞经贸学校 / 信息技术 / 计算机教研组 / 机房）。

### 2. 直接对话（最常用）

在已启用本插件（或已放入技能文件夹）的对话里，原话说即可：

| 你想做的事 | 可以这样说 |
|------------|------------|
| 写一份新教案 | `帮我写第2周第1次课教案，课题一级考证辅导2` |
| 改某一节 | `把知识学习那一步改成先讲快捷键再练第3套` |
| 校验 | `帮我校验这份教案 JSON 过不过校标` |
| 对抗性审校 | `对这份教案做对抗性教学闭环审查` |
| 导出 Word | `结构校验和审查通过后导出 docx` |
| 对照样例打分 | `对照 examples 给这份教案打分` |

Agent 应先给出：课题、周次课次、三维目标要点、八步是否齐全、校验结果、docx 路径。完整 JSON 会落成文件，不会用一篇散文代替教案。

课堂流程字段兼容原有 Markdown 字符串，也支持结构化活动数组；每行可填写 `mainContent`、`teacherActivity`、`studentActivity`、`minutes` 和 `evidence`，导出 Word 时排成“教学环节 / 主要内容 / 教师活动 / 学生活动”四栏。

### 3. 斜杠命令（可选）

| 命令 | 作用 |
|------|------|
| `/write-lesson-plan` | 按技能全流程撰写或导出。可带参数：`/write-lesson-plan 第2周第1次 一级考证辅导2` |
| `/validate-lesson-plan` | 只跑结构校验。可带 JSON 路径：`/validate-lesson-plan plan.json` |
| `/adversarial-review-lesson-plan` | 独立子 Agent 进行一轮最强反例审查。 |

审校使用独立子代理 `lesson-plan-reviewer`，它不改教案，只尝试用最强反例推翻目标、活动、任务和考核的教学闭环。修复必须交给另一 Agent；不支持子代理的宿主用 `role_simulation` 执行同一量规。

### 4. Agent 实际会做什么

技能文件是 `skills/lesson-plan-design/SKILL.md`。顺序固定，不要跳：

1. 读 `references/schema.md`（字段名、八步标题）
2. 读 `CATALOG.md`，打开 `examples/` 里**最接近**的一份 JSON 当结构金标准
3. 用 `templates/empty-plan.json` 填完整教案；缺周次/课次/课题则先问
4. **导出前必须**运行校验（失败先改，禁止带错导出）：

```bash
py -3 skills/lesson-plan-design/scripts/validate.py <教案.json>
```

5. 结构通过后，由独立审校 Agent 生成同目录 `教案.review.json`；它每轮只提交一个最强反例，或显式声明无反例。报告保存本轮教案快照与工具版本；复审轮次必须为上一轮加一，同一教案重复审校会标记 `duplicateReview`。报告记录 `independence`（`native_subagent`、`role_simulation`、`human`）；严格模式拒绝角色模拟，宽松模式允许但在 Word 中标注。`blocker`/`major` 必须修复并复审，或由教师实名说明原因放行；`minor` 须由教师实名接受后才能导出。放行/接受记录幂等，重复提交不会追加；理由至少 6 字；放行者与任课教师不一致时，严格模式拒绝，宽松模式记 `warnings`。

```bash
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/adversarial_review.py plan.json --finding finding.json --reviewer-mode native_subagent
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/adversarial_review.py plan.json --no-counterexample --reviewer-mode native_subagent
```

6. 当前审查报告哈希匹配且门禁通过后再导出：

```bash
py -3 skills/lesson-plan-design/scripts/export_docx.py <教案.json> -o <输出.docx>
```

对照样例打分（可选）：

```bash
py -3 skills/lesson-plan-design/scripts/score.py <教案.json>
```

评分维度：目标可测 25、任务对应 25、考核闭环 20、流程完整 20、证据可查 10；输出每个维度的得分、扣分原因与改进建议，≥85 优秀、≥70 合格。

样例库索引 `examples/index.json` 由脚本生成；`--check` 校验 7 份样例的 `planHash` 与元信息，过期、缺失或多余样例都会报错：

```bash
py -3 skills/lesson-plan-design/scripts/sync_examples.py --check
py -3 skills/lesson-plan-design/scripts/sync_examples.py --write
```

修订某一节时改 JSON 对应字段，再跑步骤 4 和 5；旧报告会因教案内容哈希不匹配而自动失效。飞书没有 Hooks 时，这些步骤仍由技能强制执行。

---

## 技能目录（方便对照阅读）

路径：`skills/lesson-plan-design/`

| 文件 / 目录 | 给谁看 | 干什么 |
|-------------|--------|--------|
| `SKILL.md` | Agent | 短流程：读什么、校验、导出 |
| `RULES.md` | Agent | 五条硬约束（结构优先、缺输入先问、导出前校验…） |
| `CATALOG.md` | Agent | 7 份金标准索引（周次/课次/课题） |
| `references/schema.md` | Agent | 校标字段与八步名称 |
| `references/validation.md` | Agent | 校验规则说明 |
| `templates/empty-plan.json` | Agent | 空骨架 |
| `examples/*.json` | Agent | 金标准，只打开最接近的一份 |
| `scripts/validate.py` | 本机 Python | 结构校验，退出码 0 才合格 |
| `scripts/adversarial_review.py` | 本机 Python | 对抗审查报告、复审和教师放行 |
| `scripts/export_docx.py` | 本机 Python | 仅在当前审查报告门禁通过时 JSON → Word |
| `scripts/draft.py` | 本机 Python | 按周次/课次/课题出草稿 JSON |
| `scripts/score.py` | 本机 Python | 对照 examples 打结构分 |
| `test/index.py` | 本机 Python | 导入并运行本技能全部单元测试 |

八步流程在 JSON 的 `activityFlow` 里，标题固定为：复习与导入 → 明确学习目标 → 知识学习 → 工作任务实施 → 课程考核 → 课堂小结 → 布置作业 → 教学反思。

现成金标准课题（一级考证辅导 1–7）见 `CATALOG.md`。

配套技能（与主流程并列）：

| 路径 | 干什么 |
|------|--------|
| `skills/formatting-lesson-docx/` | 教案 Markdown 子集 → Word 原生样式，可选 `mediaAssets` 嵌图 |
| `skills/capturing-ebook-pages/` | 本地 PDF/DOCX/PPT(X) 截成 PNG 并写 manifest |

---

## 不经过对话、自己跑脚本

在仓库根目录（命令统一使用 `py -3`；若本机只有 `python`，把 `py -3` 换成 `python`）：

```bash
# 按周次课次出一份草稿 JSON
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/draft.py --week 2 --session 1 --title 一级考证辅导2 --out plan.json

# 校验（不合格会打印 issues，退出码非 0）
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/validate.py plan.json

# 生成与教案哈希绑定的审查报告（有反例用 --finding，无反例用 --no-counterexample）
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/adversarial_review.py plan.json --no-counterexample --reviewer-mode native_subagent

# 门禁通过后导出 Word
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/export_docx.py plan.json -o 教案.docx

# 严格模式：任课教师、教学对象、授课日期为空时拒绝导出
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/export_docx.py plan.json -o 教案.docx --strict-metadata

# 校验全部金标准 / 跑各技能单元测试
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/validate.py --examples
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/test/index.py
py -3 plugins/lesson-plan-design/skills/formatting-lesson-docx/test/index.py
py -3 plugins/lesson-plan-design/skills/capturing-ebook-pages/test/index.py
```

一键全量（单元 + 金标准 + fixtures + 布局）：`py -3 scripts/run_all_tests.py`；任一失败返回非 0，`--json` 输出机器可读汇总，`--only` 可只跑单个套件。

故意缺「知识目标」应失败。导出前必须结构校验通过、审查报告与当前教案哈希匹配，并且没有未处理的 `blocker`/`major`/`minor`；`blocker`/`major` 由教师实名放行，`minor` 由教师实名接受。无反例时必须使用 `--no-counterexample`，不能省略审校声明。导出后 JSON 带 `selfCheck`（文档、页脚、页码、引擎版本、`planHash`、媒体哈希）；页脚含页码、引擎版本和哈希前 12 位；缺图会写「图片缺失」占位并在 `warnings` 中提示。

CLI 错误契约：成功只写 stdout；失败只写 stderr，格式为 `{"ok": false, "error": {"code": "...", "message": "...", "hint": "..."}}`；退出码 0 成功、1 输入或业务失败、2 参数用法错误。

MCP 工具包括：`get_lesson_template`、`draft_lesson_plan`、`validate_lesson_plan`、`start_adversarial_review`、`read_lesson_review`、`record_teacher_override`、`export_lesson_docx`、`score_against_samples`。Agent 连上 `lesson-plan` 服务后可直接调，不必手敲命令。

工具调用按 `inputSchema` 校验：参数缺失或类型错误返回 `-32602`，未知工具 `-32601`，坏 JSON 行 `-32700`，工具内部异常 `-32603`；错误不会终止 stdio 服务，后续请求继续处理。

---

## 分层（给改插件的人）

Codex harness：**Rules 常驻、Skill 按需、Examples 金标准、Hooks 确定性校验**。

| 层 | 路径 |
|----|------|
| 常驻规则 | `AGENTS.md` / `RULES.md` |
| 斜杠命令 | `commands/write-lesson-plan.md` |
| 审校子代理 | `agents/lesson-plan-reviewer.md` |
| Hooks | `hooks/hooks.json` → `scripts/session-start.py` 等 |
| 技能 | `skills/lesson-plan-design/SKILL.md` |
| 金标准 | `skills/lesson-plan-design/examples/*.json`（7 份） |
| 校验/导出 | `skills/lesson-plan-design/scripts/` |
| 领域组件 | `scripts/lesson_plan/`（model/validation/scoring/review/gate/examples/draft） |
| DOCX 组件 | `scripts/docx_export/`（layout/content/metadata/footer/selfcheck/build） |
| MCP 组件 | `scripts/mcp_lesson/`（schema/errors/tools/transport） |
| 清单 | `.codex-plugin` / `.qoder-plugin` / `.codebuddy-plugin` / `.claude-plugin` / `.cursor-plugin` |
| MCP | `.mcp.json` → `scripts/mcp_server.py` |

---

## 安装

- Cursor / Claude Code / Codex：[docs/ide-setup.md](../../docs/ide-setup.md)
- 飞书：[docs/feishu-miaoda-setup.md](../../docs/feishu-miaoda-setup.md)
- Qoder：[docs/qoder-setup.md](../../docs/qoder-setup.md)
- CodeBuddy：[docs/codebuddy-setup.md](../../docs/codebuddy-setup.md)
