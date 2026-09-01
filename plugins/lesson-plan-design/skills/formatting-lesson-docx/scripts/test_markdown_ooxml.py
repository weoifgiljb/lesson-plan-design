# -*- coding: utf-8 -*-
"""Markdown 子集解析与 OOXML 渲染测试。"""
from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from markdown_ooxml import DocxPackage, parse_markdown

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


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


class TestRenderOoxml(unittest.TestCase):
    def test_plain_text_has_no_bold(self) -> None:
        pkg = DocxPackage()
        xml = pkg.render_markdown("纯文本教案。")
        self.assertIn("纯文本教案。", xml)
        self.assertNotIn("<w:b/>", xml)

    def test_bold_emits_w_b(self) -> None:
        pkg = DocxPackage()
        xml = pkg.render_markdown("常见错误：**未保存**。")
        self.assertIn("<w:b/>", xml)
        self.assertIn("未保存", xml)

    def test_ordered_list_uses_numbering(self) -> None:
        pkg = DocxPackage()
        xml = pkg.render_markdown("1. 说出问题\n2. 区分编译")
        self.assertIn("<w:numPr>", xml)
        self.assertIn("说出问题", xml)
        self.assertIn("区分编译", xml)

    def test_heading_uses_style(self) -> None:
        pkg = DocxPackage()
        xml = pkg.render_markdown("## 知识目标")
        self.assertIn("Heading2", xml)
        self.assertIn("知识目标", xml)

    def test_code_fence_preserves_and_escapes(self) -> None:
        pkg = DocxPackage()
        xml = pkg.render_markdown("```c\n#include <stdio.h>\n```")
        self.assertIn("CodeBlock", xml)
        self.assertIn("&lt;stdio.h&gt;", xml)
        self.assertNotIn("#include <stdio.h>", xml)

    def test_image_rel_and_media_part(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            png = root / "shot.png"
            png.write_bytes(PNG_1X1)
            pkg = DocxPackage(base_dir=root)
            xml = pkg.render_markdown("![截图](shot.png)")
            self.assertIn("r:embed=", xml)
            parts = pkg.zip_parts("<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body>" + xml + "</w:body></w:document>")
            self.assertIn("word/numbering.xml", parts)
            self.assertIn("word/styles.xml", parts)
            media = [k for k in parts if k.startswith("word/media/")]
            self.assertEqual(len(media), 1)
            rels = parts["word/_rels/document.xml.rels"]
            if isinstance(rels, bytes):
                rels = rels.decode("utf-8")
            self.assertIn("/image", rels)


class TestExportDocxFormat(unittest.TestCase):
    def test_export_splits_flow_and_renders_markdown(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lesson-plan-design" / "scripts"))
        from export_docx import export_docx
        from lib import draft_plan

        plan = draft_plan(1, 1, "认识 C 语言")
        plan["knowledgeGoals"] = "1. 说出用途\n2. 区分编译\n\n常见错误：**未保存**。"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "demo.docx"
            png = Path(tmp) / "page-003.png"
            png.write_bytes(PNG_1X1)
            plan["mediaAssets"] = [
                {
                    "path": str(png),
                    "caption": "教材第3页",
                    "attachTo": "knowledgeLearning",
                }
            ]
            export_docx(plan, out, base_dir=Path(tmp))
            with zipfile.ZipFile(out) as zf:
                names = set(zf.namelist())
                self.assertIn("word/numbering.xml", names)
                self.assertIn("word/styles.xml", names)
                document = zf.read("word/document.xml").decode("utf-8")
                rels = zf.read("word/_rels/document.xml.rels").decode("utf-8")
            self.assertIn("<w:b/>", document)
            self.assertGreaterEqual(document.count("<w:tr>"), 16)
            self.assertIn("一、复习与导入新课", document)
            self.assertIn("三、知识学习", document)
            self.assertIn("word/media/", "\n".join(names))
            self.assertIn("/image", rels)


if __name__ == "__main__":
    unittest.main()
