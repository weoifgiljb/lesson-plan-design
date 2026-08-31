# -*- coding: utf-8 -*-
"""教案校验与草稿的单元测试。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_docx import export_docx
from lib import draft_plan, load_examples, score_against_examples, validate_plan


class TestLessonPlan(unittest.TestCase):
    def test_examples_all_valid(self) -> None:
        items = load_examples()
        self.assertEqual(len(items), 7)
        for path, plan in items:
            result = validate_plan(plan)
            self.assertTrue(result["ok"], f"{path.name}: {result['issues']}")

    def test_draft_valid(self) -> None:
        plan = draft_plan(2, 1, "一级考证辅导2", content_detail="第3、4套")
        result = validate_plan(plan)
        self.assertTrue(result["ok"], result["issues"])
        self.assertIn("必须完成", plan["activityFlow"]["taskImplementation"])

    def test_missing_knowledge_goals_fails(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["knowledgeGoals"] = ""
        result = validate_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any(i["path"] == "knowledgeGoals" for i in result["issues"]))

    def test_score_gold(self) -> None:
        items = load_examples()
        score = score_against_examples(items[0][1])
        self.assertGreaterEqual(score["ratio"], 0.95)

    def test_export_docx(self) -> None:
        plan = draft_plan(1, 2, "一级考证辅导1")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "demo.docx"
            saved = export_docx(plan, out)
            self.assertGreater(saved.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
