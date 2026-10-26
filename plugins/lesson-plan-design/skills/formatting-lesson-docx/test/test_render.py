# -*- coding: utf-8 -*-
"""Markdown 子集 → OOXML 渲染。"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from support import PNG_1X1, png_rgba, tempdir
from markdown_ooxml import DocxPackage


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
        with tempdir() as tmp:
            root = Path(tmp)
            png = root / "shot.png"
            png.write_bytes(PNG_1X1)
            pkg = DocxPackage(base_dir=root)
            xml = pkg.render_markdown("![截图](shot.png)")
            self.assertIn("r:embed=", xml)
            parts = pkg.zip_parts(
                "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body>"
                + xml
                + "</w:body></w:document>"
            )
            self.assertIn("word/numbering.xml", parts)
            self.assertIn("word/styles.xml", parts)
            media = [k for k in parts if k.startswith("word/media/")]
            self.assertEqual(len(media), 1)
            rels = parts["word/_rels/document.xml.rels"]
            if isinstance(rels, bytes):
                rels = rels.decode("utf-8")
            self.assertIn("/image", rels)

    def test_image_alt_quotes_are_xml_escaped(self) -> None:
        with tempdir() as tmp:
            root = Path(tmp)
            png = root / "shot.png"
            png.write_bytes(PNG_1X1)
            pkg = DocxPackage(base_dir=root)
            xml = pkg.image_drawing("shot.png", alt='page"3')
            self.assertIn("&quot;", xml)
            self.assertNotIn('name="page"3"', xml)

    def test_png_keeps_pixel_aspect_ratio(self) -> None:
        with tempdir() as tmp:
            root = Path(tmp)
            png = root / "wide.png"
            png.write_bytes(png_rgba(2, 1))
            pkg = DocxPackage(base_dir=root)
            xml = pkg.image_drawing("wide.png", alt="wide")
            self.assertIn('cx="4680000"', xml)
            self.assertIn('cy="2340000"', xml)

    def test_image_nv_ids_are_unique(self) -> None:
        with tempdir() as tmp:
            root = Path(tmp)
            (root / "a.png").write_bytes(PNG_1X1)
            (root / "b.png").write_bytes(PNG_1X1)
            pkg = DocxPackage(base_dir=root)
            xml = pkg.render_markdown("![一](a.png)\n\n![二](b.png)")
            ids = re.findall(r'<pic:cNvPr id="(\d+)"', xml)
            self.assertEqual(len(ids), 2)
            self.assertEqual(len(set(ids)), 2)
            self.assertNotIn("0", ids)
