# -*- coding: utf-8 -*-
"""教师放行审计：幂等、理由长度、教师一致性与门禁一一对应。"""
from __future__ import annotations

import unittest

from support import SKILL_DIR  # noqa: F401  # 先把 scripts 加入 sys.path
from lib import (
    MIN_OVERRIDE_REASON,
    TOOL_VERSION,
    adversarial_review,
    draft_plan,
    export_gate,
    plan_hash,
    record_teacher_override,
)


def _major_report(plan: dict) -> tuple[dict, str]:
    plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
    report = adversarial_review(plan, reviewer="native_subagent")
    return report, report["findings"][0]["id"]


class TestOverrideAudit(unittest.TestCase):
    def test_same_override_is_idempotent(self) -> None:
        plan = draft_plan(1, 1, "幂等课题", teacher="张老师")
        report, finding_id = _major_report(plan)
        first = record_teacher_override(
            report, finding_id, teacher="张老师", reason="本课先保留评分量表", plan=plan,
        )
        second = record_teacher_override(
            report, finding_id, teacher="张老师", reason="本课先保留评分量表", plan=plan,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(report["overrides"]), 1)
        self.assertEqual(report["status"], "passed_with_override")
        self.assertEqual(first["toolVersion"], TOOL_VERSION)
        self.assertEqual(first["planHash"], plan_hash(plan))
        self.assertTrue(first["approvedAt"])

    def test_changed_reason_after_override_is_rejected(self) -> None:
        plan = draft_plan(1, 1, "幂等课题", teacher="张老师")
        report, finding_id = _major_report(plan)
        record_teacher_override(
            report, finding_id, teacher="张老师", reason="本课先保留评分量表", plan=plan,
        )
        with self.assertRaises(ValueError):
            record_teacher_override(
                report, finding_id, teacher="张老师", reason="换一个更长的放行理由", plan=plan,
            )
        self.assertEqual(len(report["overrides"]), 1)

    def test_short_reason_is_rejected(self) -> None:
        plan = draft_plan(1, 1, "理由课题", teacher="张老师")
        report, finding_id = _major_report(plan)
        with self.assertRaises(ValueError):
            record_teacher_override(report, finding_id, teacher="张老师", reason="同意", plan=plan)
        with self.assertRaises(ValueError):
            record_teacher_override(report, finding_id, teacher="张老师", reason="", plan=plan)
        self.assertEqual(len(report["overrides"]), 0)
        self.assertGreaterEqual(MIN_OVERRIDE_REASON, 6)

    def test_teacher_mismatch_lenient_records_warning(self) -> None:
        plan = draft_plan(1, 1, "教师课题", teacher="张老师")
        report, finding_id = _major_report(plan)
        override = record_teacher_override(
            report, finding_id, teacher="李老师", reason="本课先保留评分量表", plan=plan,
        )
        self.assertTrue(override["warnings"])
        self.assertTrue(report["warnings"])
        self.assertTrue(export_gate(plan, report)["ok"])

    def test_teacher_mismatch_strict_is_rejected(self) -> None:
        plan = draft_plan(1, 1, "教师课题", teacher="张老师")
        report, finding_id = _major_report(plan)
        with self.assertRaises(ValueError):
            record_teacher_override(
                report, finding_id, teacher="李老师", reason="本课先保留评分量表",
                plan=plan, strict_teacher=True,
            )
        self.assertEqual(len(report["overrides"]), 0)

    def test_gate_rejects_override_for_missing_finding(self) -> None:
        plan = draft_plan(1, 1, "门禁课题", teacher="张老师")
        report = adversarial_review(plan, reviewer="native_subagent", no_counterexample=True)
        report["overrides"].append({
            "findingId": "not-a-finding",
            "kind": "teacher_override",
            "teacher": "张老师",
            "reason": "本课先保留评分量表",
            "planHash": plan_hash(plan),
            "toolVersion": TOOL_VERSION,
        })
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertIn("放行记录引用了不存在的问题", result["reasons"])

    def test_gate_rejects_duplicate_override_records(self) -> None:
        plan = draft_plan(1, 1, "门禁课题", teacher="张老师")
        report, finding_id = _major_report(plan)
        override = record_teacher_override(
            report, finding_id, teacher="张老师", reason="本课先保留评分量表", plan=plan,
        )
        report["overrides"].append(dict(override))
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertIn("同一问题存在多条放行记录", result["reasons"])
