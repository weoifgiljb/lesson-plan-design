# -*- coding: utf-8 -*-
"""结构校验、草稿与金标准打分。"""
from __future__ import annotations

import unittest

from support import SKILL_DIR  # noqa: F401  # 先把 scripts 加入 sys.path
from lib import draft_plan, load_examples, score_against_examples, validate_plan


class TestValidate(unittest.TestCase):
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

    def test_score_dimensions_cover_five_areas(self) -> None:
        score = score_against_examples(load_examples()[0][1])
        self.assertEqual(score["score"], 100)
        self.assertEqual(score["level"], "优秀")
        ids = [item["id"] for item in score["dimensions"]]
        self.assertEqual(ids, ["goal", "task", "assessment", "flow", "evidence"])
        self.assertEqual(sum(item["weight"] for item in score["dimensions"]), 100)

    def test_score_missing_plan_has_zero_and_reasons(self) -> None:
        score = score_against_examples({})
        self.assertEqual(score["score"], 0)
        self.assertEqual(score["level"], "待改进")
        for dimension in score["dimensions"]:
            self.assertTrue(dimension["reasons"], dimension["id"])

    def test_score_is_deterministic(self) -> None:
        plan = draft_plan(1, 1, "确定性课题")
        self.assertEqual(score_against_examples(plan), score_against_examples(plan))

    def test_score_explains_deduction(self) -> None:
        plan = draft_plan(1, 1, "扣分说明")
        plan["activityFlow"]["assessment"] = "过程考核：30"
        score = score_against_examples(plan)
        self.assertLess(score["score"], 100)
        assessment = next(item for item in score["dimensions"] if item["id"] == "assessment")
        self.assertTrue(assessment["reasons"])
        self.assertTrue(assessment["suggestions"])

    def test_structured_activity_requires_main_content(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["knowledgeLearning"] = [
            {"teacherActivity": "演示", "studentActivity": "跟做"}
        ]
        result = validate_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any(i["path"] == "activityFlow.knowledgeLearning[0].mainContent" for i in result["issues"]))

    def test_structured_activity_is_valid_with_evidence(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["taskImplementation"] = [
            {
                "mainContent": "完成个人名片程序",
                "teacherActivity": "演示调试",
                "studentActivity": "编写并运行",
                "minutes": 20,
                "evidence": "提交 C01_学号.c",
            }
        ]
        result = validate_plan(plan)
        self.assertTrue(result["ok"], result["issues"])

    def test_c_language_draft_uses_structured_topic_template(self) -> None:
        plan = draft_plan(1, 1, "认识C语言与Dev-C++开发环境")
        flow = plan["activityFlow"]
        self.assertIsInstance(flow["knowledgeLearning"], list)
        self.assertTrue(flow["knowledgeLearning"][0]["mainContent"])
        self.assertTrue(flow["taskImplementation"][0]["studentActivity"])
        self.assertTrue(flow["taskImplementation"][0]["evidence"])
