# -*- coding: utf-8 -*-
"""教案库规则与版本差异（纯函数）。"""
from __future__ import annotations

import unittest

from app.domain import diff, library


class TestLibraryRules(unittest.TestCase):
    def test_page_params_are_clamped(self) -> None:
        self.assertEqual(library.page_params(None, None), (1, 20, 0))
        self.assertEqual(library.page_params(0, 0), (1, 20, 0))
        self.assertEqual(library.page_params(3, 500), (3, 100, 200))

    def test_scope_for_roles(self) -> None:
        self.assertEqual(library.scope_for({"id": 7, "role": "teacher"}), {"owner_id": 7})
        self.assertEqual(library.scope_for({"id": 7, "role": "lead", "group_name": "计算机"}), {"group_name": "计算机"})
        self.assertEqual(library.scope_for({"id": 7, "role": "lead", "group_name": ""}), {"owner_id": 7})
        self.assertEqual(library.scope_for({"id": 7, "role": "admin"}), {})

    def test_can_view_matrix(self) -> None:
        self.assertTrue(library.can_view("teacher", 1, "", 1, ""))
        self.assertFalse(library.can_view("teacher", 1, "", 2, ""))
        self.assertTrue(library.can_view("lead", 3, "计算机", 1, "计算机"))
        self.assertFalse(library.can_view("lead", 3, "计算机", 2, "英语"))
        self.assertFalse(library.can_view("lead", 3, "", 1, ""))
        self.assertTrue(library.can_view("admin", 3, "", 1, ""))

    def test_can_delete(self) -> None:
        self.assertTrue(library.can_delete("teacher", 1, 1))
        self.assertFalse(library.can_delete("teacher", 1, 2))
        self.assertTrue(library.can_delete("lead", 1, 1))
        self.assertFalse(library.can_delete("lead", 1, 2))
        self.assertTrue(library.can_delete("admin", 9, 1))


class TestPlanDiff(unittest.TestCase):
    def test_nested_changes_have_paths(self) -> None:
        before = {"contentTitle": "课题", "activityFlow": {"summary": "旧小结"}, "knowledgeGoals": "a"}
        after = {"contentTitle": "课题", "activityFlow": {"summary": "新小结"}, "knowledgeGoals": "b"}
        changes = {item["path"]: item for item in diff.diff_plans(before, after)}
        self.assertIn("activityFlow.summary", changes)
        self.assertEqual(changes["activityFlow.summary"]["before"], "旧小结")
        self.assertEqual(changes["knowledgeGoals"]["after"], "b")
        self.assertEqual(len(changes), 2)

    def test_structured_activity_rows_are_compared_by_index(self) -> None:
        before = {"activityFlow": {"taskImplementation": [{"mainContent": "第1套", "minutes": 20}]}}
        after = {"activityFlow": {"taskImplementation": [{"mainContent": "第2套", "minutes": 20}]}}
        changes = diff.diff_plans(before, after)
        self.assertEqual([item["path"] for item in changes], ["activityFlow.taskImplementation[0].mainContent"])

    def test_identical_plans_have_no_changes(self) -> None:
        plan = {"a": 1, "b": {"c": [1, 2]}}
        self.assertEqual(diff.diff_plans(plan, plan), [])


if __name__ == "__main__":
    unittest.main()
