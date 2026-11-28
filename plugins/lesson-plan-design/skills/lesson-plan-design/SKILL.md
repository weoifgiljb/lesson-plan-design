---
name: lesson-plan-design
description: >
  撰写、修订、校验或导出职教校标教案（东莞经贸学校信息技术，三维目标与八步流程）。
  用户提到写教案、改教案、一级考证、周次课次、机房实训时使用。
---

# 教案设计（短流程）

硬约束见同目录 `RULES.md`。不要把样例全文贴进回复；按需打开下列文件。

## 必须按序

1. Read `references/schema.md`（字段与八步名称）。
2. Read `CATALOG.md`，打开 `examples/` 中最接近的一份 JSON 作为结构金标准。
3. 以 `templates/empty-plan.json` 为骨架填写完整教案（缺周次/课次/课题则先问）。
4. **导出前必须执行**（飞书无 hooks 时同样强制）：

```bash
py -3 scripts/validate.py <教案.json>
```

退出码非 0 则按 issues 修改后再跑，禁止跳过。

5. 结构通过后，由独立审校 Agent 产出一个最强教学闭环反例并写入报告。Codex 使用独立子 Agent 审校；不支持子 Agent 的宿主使用 `role_simulation` 串行模拟同一量规。报告保存本轮教案快照与工具版本；复审轮次必须为上一轮加一，同一教案重复审校会标记 `duplicateReview`。报告记录 `independence`；严格模式拒绝角色模拟，宽松模式允许但在 Word 中标注。出现 `blocker`/`major` 时交由修复 Agent 修改教案并复审；只有教师实名说明原因后可放行；`minor` 须由教师实名接受。放行/接受记录幂等，理由至少 6 字；放行者与任课教师不一致时，严格模式拒绝，宽松模式记 `warnings`。任一未闭环问题都会阻断导出。无反例时必须显式声明，禁止省略参数直接通过。

```bash
py -3 scripts/adversarial_review.py <教案.json> --finding '<JSON>' --reviewer-mode native_subagent
py -3 scripts/adversarial_review.py <教案.json> --no-counterexample --reviewer-mode native_subagent
```

6. 当前报告有效且门禁通过后再导出：

```bash
py -3 scripts/export_docx.py <教案.json> -o <输出.docx>
```

默认文件名含课题、周次课次与版本；目标已存在时必须加 `--force`，覆盖前保留 `.bak`。`--history` 列出每次导出的时间、哈希与路径，`--open-version N` 输出对应版本路径：

```bash
py -3 scripts/export_docx.py <教案.json> --history
py -3 scripts/export_docx.py <教案.json> --open-version 1
```

加 `--strict-metadata` 时，任课教师、教学对象或授课日期为空会拒绝导出；不加则用 `____` 占位。CLI 失败只写 stderr，统一为 `{"ok": false, "error": {"code": "...", "message": "...", "hint": "..."}}`；退出码 0 成功、1 输入或业务失败、2 参数用法错误。

长文本可用 Markdown 子集（`**粗体**`、`1. ` 列表、围栏代码、`![说明](相对路径)`），由 `formatting-lesson-docx` 渲成 Word 原生样式。可选 `mediaAssets` 嵌教材截图；截图先走 `capturing-ebook-pages`。金标准里的 `1、` 仍按普通段落导出。页脚含页码、引擎版本与 `planHash` 前 12 位；缺图写「图片缺失」占位并给 `warnings`；导出后返回 `selfCheck` 校验文档、页脚、页码、媒体哈希。

修订某一节用字段级命令，不要手工整文件重写；命令会拒绝未知路径、原子替换原文件，并在旧报告失效时明确提示：

```bash
py -3 scripts/revise_plan.py <教案.json> --set "contentTitle=新课题"
py -3 scripts/revise_plan.py <教案.json> --set "activityFlow.assessment=1、过程考核：..." --dry-run
py -3 scripts/diff_plans.py <旧版.json> <新版.json>
```

一键流程串起草稿、校验、审校与导出，`--until` 可在任一步停下，`--plan` 可从已有教案续跑：

```bash
py -3 scripts/lesson_flow.py --week 2 --session 1 --title 一级考证辅导2 --out-dir . --until validate
py -3 scripts/lesson_flow.py --plan ./教案_一级考证辅导2_第2周第1次.json
```

`--force` 允许覆盖 docx 并保留 `.bak`；校验失败退出码 1，审校未通过退出码 2。

对照样例打分（可选）：`py -3 scripts/score.py <教案.json>`。评分维度为目标 25、任务 25、考核 20、流程 20、证据 10，输出维度得分、扣分原因与改进建议；≥85 优秀、≥70 合格。样例库索引由 `sync_examples.py --write` 生成，`--check` 校验哈希与元信息。

## 输出

给用户：课题、周次课次、三维目标要点、八步是否齐全、校验结果、docx 路径。完整 JSON 可附文件，不要用散文代替结构。
