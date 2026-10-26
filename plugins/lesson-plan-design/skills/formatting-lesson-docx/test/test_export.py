# -*- coding: utf-8 -*-
"""教案导出接入 Markdown 与 mediaAssets。"""
from __future__ import annotations

import sys
import unittest
import zipfile
from pathlib import Path

from support import PNG_1X1, SKILLS_DIR, tempdir

sys.path.insert(0, str(SKILLS_DIR / "lesson-plan-design" / "scripts"))
from export_docx import (
    ENGINE_VERSION,
    _split_key_points,
    export_docx,
    export_docx_result,
    self_check,
)
from lib import draft_plan


def _document_xml(plan: dict) -> str:
    with tempdir() as tmp:
        out = Path(tmp) / "plan.docx"
        export_docx(plan, out, base_dir=Path(tmp))
        with zipfile.ZipFile(out) as zf:
            return zf.read("word/document.xml").decode("utf-8")


class TestExportDocxFormat(unittest.TestCase):
    def test_footer_has_page_number_and_engine(self) -> None:
        plan = draft_plan(1, 1, "页脚检查")
        with tempdir() as tmp:
            out = Path(tmp) / "footer.docx"
            result = export_docx_result(plan, out)
            with zipfile.ZipFile(out) as zf:
                names = set(zf.namelist())
                document = zf.read("word/document.xml").decode("utf-8")
                footer = zf.read("word/footer1.xml").decode("utf-8")
                rels = zf.read("word/_rels/document.xml.rels").decode("utf-8")
                content_types = zf.read("[Content_Types].xml").decode("utf-8")
            check = self_check(out, plan, result["media"])
        self.assertIn("word/footer1.xml", names)
        self.assertIn('w:instr=" PAGE "', footer)
        self.assertIn(ENGINE_VERSION, footer)
        self.assertIn("footerReference", document)
        self.assertIn("footer1.xml", rels)
        self.assertIn("footer1.xml", content_types)
        self.assertTrue(check["ok"], check)

    def test_missing_media_uses_placeholder_and_warning(self) -> None:
        plan = draft_plan(1, 1, "缺图检查")
        plan["mediaAssets"] = [{
            "path": "missing.png",
            "caption": "教材第 3 页",
            "attachTo": "knowledgeLearning",
        }]
        with tempdir() as tmp:
            out = Path(tmp) / "missing.docx"
            result = export_docx_result(plan, out, base_dir=Path(tmp))
            with zipfile.ZipFile(out) as zf:
                document = zf.read("word/document.xml").decode("utf-8")
            check = self_check(out, plan, result["media"])
        self.assertIn("图片缺失", document)
        self.assertTrue(any("missing.png" in item for item in result["warnings"]))
        self.assertTrue(check["ok"], check)

    def test_self_check_detects_tampered_media(self) -> None:
        plan = draft_plan(1, 1, "篡改检查")
        with tempdir() as tmp:
            root = Path(tmp)
            png = root / "page.png"
            png.write_bytes(PNG_1X1)
            plan["mediaAssets"] = [{
                "path": str(png),
                "caption": "教材页",
                "attachTo": "knowledgeLearning",
            }]
            out = root / "media.docx"
            result = export_docx_result(plan, out, base_dir=root)
            tampered = root / "tampered.docx"
            with zipfile.ZipFile(out) as src, zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_DEFLATED) as dst:
                for item in src.infolist():
                    data = src.read(item.filename)
                    if item.filename.startswith("word/media/"):
                        data = b"tampered"
                    dst.writestr(item, data)
            check = self_check(tampered, plan, result["media"])
        self.assertFalse(check["ok"])
        self.assertFalse(check["checks"]["media"])

    def test_export_splits_flow_and_renders_markdown(self) -> None:
        plan = draft_plan(1, 1, "认识 C 语言")
        plan["knowledgeGoals"] = "1. 说出用途\n2. 区分编译\n\n常见错误：**未保存**。"
        with tempdir() as tmp:
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
                document = zf.read("word/document.xml").decode("utf-8")
                rels = zf.read("word/_rels/document.xml.rels").decode("utf-8")
            self.assertIn("word/numbering.xml", names)
            self.assertIn("word/styles.xml", names)
            self.assertIn("<w:b/>", document)
            self.assertGreaterEqual(document.count("<w:tr>"), 17)
            self.assertIn("课前组织", document)
            self.assertIn("知识学习", document)
            self.assertIn("课程考核", document)
            self.assertIn("word/media/", "\n".join(names))
            self.assertIn("/image", rels)

    def test_title_run_uses_black_font(self) -> None:
        document = _document_xml(draft_plan(1, 1, "标题字体"))
        self.assertIn('w:rFonts w:ascii="黑体" w:eastAsia="黑体"', document)

    def test_title_uses_specific_content_topic(self) -> None:
        document = _document_xml(draft_plan(1, 1, "认识 C 语言与 Dev-C++"))
        self.assertIn("《认识 C 语言与 Dev-C++》", document)
        self.assertNotIn("东莞经贸学校教案", document)

    def test_header_includes_meta_and_purpose(self) -> None:
        plan = draft_plan(2, 1, "导出表头元信息", teacher="龙琼芳", teaching_object="计算机1班")
        plan["teachingPurpose"] = "帮助学生完成可观察的上机任务。"
        plan["academicYear"] = "2026-2027"
        document = _document_xml(plan)
        self.assertIn("2026-2027学年", document)
        self.assertIn("任课教师：龙琼芳", document)
        self.assertIn("教学对象：计算机1班", document)
        self.assertIn("第2周第1次", document)
        self.assertIn("教学目的", document)
        self.assertIn("帮助学生完成可观察的上机任务。", document)

    def test_split_key_and_difficult_points(self) -> None:
        self.assertEqual(
            _split_key_points("重点：编辑—编译—运行。难点：区分报错与结果。"),
            ("编辑—编译—运行。", "区分报错与结果。"),
        )
        plan = draft_plan(1, 1, "重难点分写")
        plan["keyPoints"] = "重点：for 三段式。难点：循环边界。"
        document = _document_xml(plan)
        key_pos = document.index("教学重点")
        diff_pos = document.index("教学难点")
        method_pos = document.index("教学方法")
        key_cell = document[key_pos:diff_pos]
        diff_cell = document[diff_pos:method_pos]
        self.assertIn("for 三段式", key_cell)
        self.assertNotIn("循环边界", key_cell)
        self.assertIn("循环边界", diff_cell)
        self.assertNotIn("for 三段式", diff_cell)

    def test_structured_flow_uses_reference_grid_and_a4_margins(self) -> None:
        plan = draft_plan(1, 1, "认识 C 语言")
        plan["activityFlow"]["taskImplementation"] = [
            {
                "mainContent": "源文件、编译与运行",
                "teacherActivity": "演示新建并编译 C 文件",
                "studentActivity": "完成操作并提交截图",
                "minutes": 20,
                "evidence": "生成 C01.c",
            }
        ]
        document = _document_xml(plan)
        self.assertIn("教学环节", document)
        self.assertIn("主要内容", document)
        self.assertIn("教学活动", document)
        self.assertIn("教师活动", document)
        self.assertIn("学生活动", document)
        self.assertIn("生成 C01.c", document)
        self.assertIn("（20分钟）", document)
        self.assertIn('w:w="11906" w:h="16838"', document)
        self.assertIn('w:left="1800"', document)
        self.assertIn('w:right="1800"', document)
        self.assertNotIn("D6E3F8", document)
        self.assertIn(
            '<w:gridCol w:w="827"/><w:gridCol w:w="274"/><w:gridCol w:w="1275"/>'
            '<w:gridCol w:w="1985"/><w:gridCol w:w="2551"/><w:gridCol w:w="664"/>'
            '<w:gridCol w:w="1001"/><w:gridCol w:w="711"/>',
            document,
        )

    def test_only_task_implementation_uses_activity_columns(self) -> None:
        plan = draft_plan(1, 1, "仅任务实施分列")
        plan["activityFlow"]["introduction"] = {
            "mainContent": "导入内容",
            "teacherActivity": "导入教师活动",
            "studentActivity": "导入学生活动",
            "evidence": "导入产出",
        }
        plan["activityFlow"]["taskImplementation"] = {
            "mainContent": "任务内容",
            "teacherActivity": "任务教师活动",
            "studentActivity": "任务学生活动",
            "evidence": "任务产出",
        }
        document = _document_xml(plan)
        self.assertNotIn("导入教师活动", document)
        self.assertNotIn("导入学生活动", document)
        self.assertNotIn("导入产出", document)
        self.assertEqual(document.count("教学活动"), 1)
        self.assertIn("任务教师活动", document)
        self.assertIn("任务学生活动", document)
        self.assertIn("任务产出", document)
        self.assertIn("课程考核", document)
        self.assertNotIn("任务实施与考核", document)
