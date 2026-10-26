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
                "mainContent": "必须完成：完成个人名片程序",
                "teacherActivity": "演示调试",
                "studentActivity": "编写并运行",
                "minutes": plan["plannedHours"] * 45,
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
        result = validate_plan(plan)
        self.assertTrue(result["ok"], result["issues"])

    def test_structured_task_without_must_do_fails(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["taskImplementation"] = [
            {
                "mainContent": "完成练习",
                "studentActivity": "编写并运行程序",
                "evidence": "提交结果文件",
            }
        ]
        result = validate_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(item["path"] == "activityFlow.taskImplementation" for item in result["issues"])
        )

    def test_minutes_total_mismatch_fails(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        tolerance = 5
        expected = plan["plannedHours"] * 45
        plan["activityFlow"]["introduction"] = [
            {"mainContent": "导入", "minutes": expected + tolerance}
        ]
        result = validate_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(item["path"] == "activityFlow" and "分钟" in item["message"] for item in result["issues"])
        )
        tolerated = validate_plan(plan, minutes_tolerance=tolerance)
        self.assertTrue(tolerated["ok"], tolerated["issues"])

    def test_missing_minutes_is_warning_only(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["introduction"] = [{"mainContent": "导入"}]
        result = validate_plan(plan)
        self.assertTrue(result["ok"], result["issues"])
        self.assertTrue(any("分钟" in item["message"] for item in result["warnings"]))

    def test_missing_week_reports_single_issue(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        del plan["week"]
        result = validate_plan(plan)
        hits = [item for item in result["issues"] if item["path"] == "week"]
        self.assertEqual(len(hits), 1)

    def test_bool_week_rejected(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["week"] = True
        result = validate_plan(plan)
        self.assertFalse(result["ok"])
        hits = [item for item in result["issues"] if item["path"] == "week"]
        self.assertEqual(len(hits), 1)
        self.assertFalse(any("不能为空" in item["message"] for item in hits))

    def test_catalog_detail_conflict_warns_by_default(self) -> None:
        plan = draft_plan(2, 1, "一级考证辅导2", content_detail="第1、2套")
        result = validate_plan(plan)
        self.assertTrue(result["ok"], result["issues"])
        self.assertTrue(any(item["path"] == "contentDetail" for item in result["warnings"]))
        strict = validate_plan(plan, strict=True)
        self.assertFalse(strict["ok"])
        self.assertTrue(any(item["path"] == "contentDetail" for item in strict["issues"]))

    def test_rule_version_and_warnings_are_exposed(self) -> None:
        result = validate_plan(draft_plan(1, 1, "测试课题"))
        self.assertEqual(result["ruleVersion"], "1.1.0")
        self.assertIsInstance(result["warnings"], list)

    def test_issue_order_is_stable(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        del plan["abilityGoals"]
        del plan["knowledgeGoals"]
        paths = [item["path"] for item in validate_plan(plan)["issues"]]
        self.assertEqual(paths, sorted(paths))
