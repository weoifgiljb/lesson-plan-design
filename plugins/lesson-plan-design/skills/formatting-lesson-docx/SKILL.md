---
name: formatting-lesson-docx
description: >
  将校标教案 JSON 中的 Markdown 子集（粗体、列表、标题、围栏代码、图片）导出为可编辑的 Word 原生样式。
  用户提到导出 Word、docx 排版、教案 Markdown、Word 里仍显示 ** 或列表标记时使用。
---

# Formatting Lesson Docx

## Instructions

1. 撰写、校验、对抗审查仍走 `lesson-plan-design`。本技能只负责 Word 渲染。
2. 长文本字段（`knowledgeGoals`、`activityFlow.*` 等）按下列 Markdown 子集填写：
   - `**粗体**`、`*斜体*`、行内代码
   - `#` 到 `###` 标题
   - `- ` 无序列表、`1. ` 有序列表
   - 围栏代码块
   - `![说明](相对路径)` 插图
3. 不要指望中文 `1、` 自动变成列表。金标准里无标记的旧文本仍按普通段落导出。C 语言 `*p` / `*q` 写成行内代码，不要用成对 `*` 当斜体。
4. 结构校验与当前审查报告通过后导出（该脚本会加载本技能的 `scripts/markdown_ooxml.py`）：

```bash
py -3 ../lesson-plan-design/scripts/export_docx.py <plan.json> -o <out.docx>
```

5. 可选字段 `mediaAssets`（不是结构校验必填）：

```json
"mediaAssets": [
  {"path": "output/ebook-captures/demo/page-003.png", "caption": "教材第3页", "attachTo": "knowledgeLearning"}
]
```

   `attachTo` 用字段名，八步可用 `knowledgeLearning` 或 `activityFlow.knowledgeLearning`。教材截图先用 `capturing-ebook-pages`。
6. 不要引入 python-docx 或 pandoc。用户正文必须 XML 转义。禁止跳过校验或审查。

## Examples

用户把知识目标写成：

```text
## 知识目标
1. 说出 C 语言能解决哪类问题
2. 区分源文件、编译、运行

常见错误：**未保存**、扩展名 `.c`。
```

导出后 Word 中应出现二级标题、编号列表、加粗和行内代码，而不是原始 `**` 标记。

金标准里的 `1、计算机基础知识理论题 2、文件管理` 仍导出为一段普通文字。

## Additional Resources

- 解析器：[scripts/markdown_ooxml.py](scripts/markdown_ooxml.py)
- 测试：[test/index.py](test/index.py)
- 教材截图：`capturing-ebook-pages`
- 教案主流程：`lesson-plan-design`
