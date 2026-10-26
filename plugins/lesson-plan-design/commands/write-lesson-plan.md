---
description: 按东莞经贸学校信息技术校标撰写或导出一份完整教案。需要周次、课次、教学内容标题。
argument-hint: "[第N周第M次] [课题]"
---

按技能 `lesson-plan-design` 执行。用户参数：$ARGUMENTS

1. 读取 `skills/lesson-plan-design/references/schema.md`
2. 用 `CATALOG.md` 对照 `examples/` 中最接近的金标准
3. 基于 `templates/empty-plan.json` 填完整教案。长文本用 Markdown 子集（`**粗体**`、`1. ` 列表、围栏代码、`![说明](相对路径)`）；C 语言标识符如 `*p` 写成行内代码。教材截图走 `capturing-ebook-pages`，写入 `mediaAssets`
4. 运行 `py -3 skills/lesson-plan-design/scripts/validate.py <教案.json>`
5. 由独立审校 Agent 产出一个最强教学闭环反例，运行 `py -3 skills/lesson-plan-design/scripts/adversarial_review.py <教案.json> --finding '<JSON>' --reviewer-mode native_subagent` 写入当前报告；无可证实反例时改用 `--no-counterexample`。`blocker`/`major` 必须由修复 Agent 处理并复审，或由教师实名放行
6. 当前报告门禁通过后再运行 `py -3 skills/lesson-plan-design/scripts/export_docx.py <教案.json>`

缺周次/课次/课题时先问。不要只输出散文。
