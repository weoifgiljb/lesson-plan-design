# -*- coding: utf-8 -*-
"""教案导出接入 Markdown 与 mediaAssets。"""
from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from support import PNG_1X1, SKILLS_DIR


class TestExportDocxFormat(unittest.TestCase):
    def test_export_splits_flow_and_renders_markdown(self) -> None:
        sys.path.insert(0, str(SKILLS_DIR / "lesson-plan-design" / "scripts"))
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

    def test_structured_flow_uses_activity_columns_and_a4_margins(self) -> None:
        sys.path.insert(0, str(SKILLS_DIR / "lesson-plan-design" / "scripts"))
        from export_docx import export_docx
        from lib import draft_plan

        plan = draft_plan(1, 1, "认识 C 语言")
        plan["activityFlow"]["knowledgeLearning"] = [
            {
                "mainContent": "源文件、编译与运行",
                "teacherActivity": "演示新建并编译 C 文件",
                "studentActivity": "完成操作并提交截图",
                "minutes": 20,
                "evidence": "生成 C01.c",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "structured.docx"
            export_docx(plan, out, base_dir=Path(tmp))
            with zipfile.ZipFile(out) as zf:
                document = zf.read("word/document.xml").decode("utf-8")
            self.assertIn("教学环节", document)
            self.assertIn("主要内容", document)
            self.assertIn("教师活动", document)
            self.assertIn("学生活动", document)
            self.assertIn("生成 C01.c", document)
            self.assertIn('w:w="11906" w:h="16838"', document)
            self.assertIn('w:left="1800"', document)
            self.assertIn('w:right="1800"', document)
            self.assertNotIn("D6E3F8", document)
