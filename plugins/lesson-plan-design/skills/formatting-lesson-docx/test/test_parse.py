# -*- coding: utf-8 -*-
"""Markdown 子集解析。"""
from __future__ import annotations

import unittest

from support import SCRIPTS_DIR  # noqa: F401
from markdown_ooxml import parse_markdown


class TestParseMarkdown(unittest.TestCase):
    def test_plain_text_is_one_paragraph(self) -> None:
        blocks = parse_markdown("帮助零基础学生建立认识。")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].kind, "paragraph")
        self.assertEqual("".join(i.text for i in blocks[0].inlines), "帮助零基础学生建立认识。")

    def test_bold_italic_and_inline_code(self) -> None:
        blocks = parse_markdown("常见错误：**未保存**、*中文标点*、扩展名 `.c`。")
        kinds = [i.kind for i in blocks[0].inlines]
        texts = [i.text for i in blocks[0].inlines]
        self.assertIn("bold", kinds)
        self.assertIn("italic", kinds)
        self.assertIn("code", kinds)
        self.assertIn("未保存", texts)
        self.assertIn("中文标点", texts)
        self.assertIn(".c", texts)

    def test_heading_lists_and_fence(self) -> None:
        source = (
            "## 知识目标\n"
            "1. 说出 C 语言能解决哪类问题\n"
            "2. 区分源文件、编译、运行\n"
            "- 遵守机房 6S\n"
            "\n"
            "```c\n"
            "#include <stdio.h>\n"
            "int main(void) { return 0; }\n"
            "```\n"
        )
        blocks = parse_markdown(source)
        kinds = [b.kind for b in blocks]
        self.assertEqual(kinds[0], "heading")
        self.assertEqual(blocks[0].level, 2)
        self.assertEqual(kinds[1], "ol_item")
        self.assertEqual(kinds[2], "ol_item")
        self.assertEqual(kinds[3], "ul_item")
        self.assertEqual(kinds[4], "code")
        self.assertIn("#include <stdio.h>", blocks[4].text)
        self.assertEqual(blocks[4].lang, "c")

    def test_standalone_image(self) -> None:
        blocks = parse_markdown("![教材第3页](pages/page-003.png)")
        self.assertEqual(blocks[0].kind, "image")
        self.assertEqual(blocks[0].alt, "教材第3页")
        self.assertEqual(blocks[0].src, "pages/page-003.png")

    def test_chinese_enumerated_text_stays_paragraph(self) -> None:
        blocks = parse_markdown("1、计算机基础知识理论题 2、文件管理")
        self.assertEqual(blocks[0].kind, "paragraph")

    def test_c_pointer_stars_are_not_italic(self) -> None:
        blocks = parse_markdown("区分 *p 与 *q 的含义")
        kinds = [item.kind for item in blocks[0].inlines]
        joined = "".join(item.text for item in blocks[0].inlines)
        self.assertNotIn("italic", kinds)
        self.assertIn("*p", joined)
        self.assertIn("*q", joined)

    def test_markdown_italic_still_works(self) -> None:
        blocks = parse_markdown("强调 *中文斜体* 即可")
        kinds = [item.kind for item in blocks[0].inlines]
        texts = [item.text for item in blocks[0].inlines]
        self.assertIn("italic", kinds)
        self.assertIn("中文斜体", texts)
