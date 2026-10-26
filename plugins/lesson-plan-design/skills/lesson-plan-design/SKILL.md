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
python scripts/validate.py <教案.json>
```

退出码非 0 则按 issues 修改后再跑，禁止跳过。

5. 结构通过后，由独立审校 Agent 产出一个最强教学闭环反例并写入报告。Codex 使用独立子 Agent 审校；不支持子 Agent 的宿主使用 `role_simulation` 串行模拟同一量规。出现 `blocker`/`major` 时交由修复 Agent 修改教案并复审；只有教师实名说明原因后可放行。无反例时必须显式声明，禁止省略参数直接通过。

```bash
python scripts/adversarial_review.py <教案.json> --finding '<JSON>' --reviewer-mode native_subagent
python scripts/adversarial_review.py <教案.json> --no-counterexample --reviewer-mode native_subagent
```

6. 当前报告有效且门禁通过后再导出：

```bash
python scripts/export_docx.py <教案.json> -o <输出.docx>
```

长文本可用 Markdown 子集（`**粗体**`、`1. ` 列表、围栏代码、`![说明](相对路径)`），由 `formatting-lesson-docx` 渲成 Word 原生样式。可选 `mediaAssets` 嵌教材截图；截图先走 `capturing-ebook-pages`。金标准里的 `1、` 仍按普通段落导出。

修订某一节时改 JSON 对应字段，再跑步骤 4 和 5；旧报告因内容哈希不匹配自动失效。

对照样例打分（可选）：`python scripts/score.py <教案.json>`。评分维度为目标 25、任务 25、考核 20、流程 20、证据 10，输出维度得分、扣分原因与改进建议；≥85 优秀、≥70 合格。

## 输出

给用户：课题、周次课次、三维目标要点、八步是否齐全、校验结果、docx 路径。完整 JSON 可附文件，不要用散文代替结构。
