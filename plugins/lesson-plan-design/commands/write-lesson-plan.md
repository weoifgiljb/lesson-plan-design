---
description: 按东莞经贸学校信息技术校标撰写或导出一份完整教案。需要周次、课次、教学内容标题。
argument-hint: "[第N周第M次] [课题]"
---

按技能 `lesson-plan-design` 执行。用户参数：$ARGUMENTS

1. 读取 `skills/lesson-plan-design/references/schema.md`
2. 用 `CATALOG.md` 对照 `examples/` 中最接近的金标准
3. 基于 `templates/empty-plan.json` 填完整教案
4. 运行 `python skills/lesson-plan-design/scripts/validate.py <教案.json>`
5. 通过后再运行 `python skills/lesson-plan-design/scripts/export_docx.py <教案.json>`

缺周次/课次/课题时先问。不要只输出散文。
