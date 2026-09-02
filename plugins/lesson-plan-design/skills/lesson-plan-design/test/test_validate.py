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
