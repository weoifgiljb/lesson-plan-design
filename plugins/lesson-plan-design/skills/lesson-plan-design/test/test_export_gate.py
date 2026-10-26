# -*- coding: utf-8 -*-
"""导出门禁与教师放行。"""
from __future__ import annotations

import unittest

from support import SKILL_DIR  # noqa: F401
from lib import (
    REVIEW_SCHEMA_VERSION,
    RUBRIC_VERSION,
    adversarial_review,
    draft_plan,
    export_gate,
    load_examples,
    plan_hash,
    record_teacher_override,
)


class TestExportGate(unittest.TestCase):
    def test_export_gate_rejects_report_for_changed_plan(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan)
        plan["activityFlow"]["assessment"] = "依据学生提交的文件和操作记录评分。"
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertIn("审查报告与当前教案内容不匹配", result["reasons"])

    def test_teacher_override_allows_current_major_finding(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan, reviewer="native_subagent")
        issue_id = report["findings"][0]["id"]
        record_teacher_override(report, issue_id, teacher="张老师", reason="本课先保留评分量表", plan=plan)
        result = export_gate(plan, report)
        self.assertTrue(result["ok"], result["reasons"])
        self.assertEqual(report["overrides"][0]["planHash"], plan_hash(plan))
        self.assertEqual(report["findings"][0]["status"], "waived")

    def test_teacher_override_rejects_non_list_overrides(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan, reviewer="native_subagent")
        report["overrides"] = {}
        with self.assertRaises(ValueError):
            record_teacher_override(
                report,
                report["findings"][0]["id"],
                teacher="张老师",
                reason="保留当前评分量表",
                plan=plan,
            )

    def test_export_gate_rejects_blank_teacher_override_fields(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan, reviewer="native_subagent")
        finding = report["findings"][0]
        finding["status"] = "waived"
        report["overrides"] = [{
            "findingId": finding["id"],
            "planHash": plan_hash(plan),
            "teacher": " ",
            "reason": " ",
        }]
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertIn("审查放行记录格式无效", result["reasons"])

    def test_waived_blocking_finding_requires_matching_teacher_override(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan)
        report["findings"][0]["status"] = "waived"
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("缺少与 waived 问题匹配的教师放行记录" in reason for reason in result["reasons"]))

    def test_export_gate_rejects_malformed_override_without_crashing(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan)
        report["overrides"] = [None]
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertIn("审查放行记录格式无效", result["reasons"])

    def test_minor_finding_does_not_block_export(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(
            plan,
            reviewer="native_subagent",
            finding={
                "id": "minor-1",
                "severity": "minor",
                "hypothesis": "flow_pseudo_loop",
                "evidence": ["课堂小结可以补充更具体的提问。"],
                "affectedPaths": ["activityFlow.summary"],
                "whyItBreaksTheLoop": "反馈证据较弱。",
                "minimalRepair": "补充一项回顾问题。",
            },
        )
        self.assertTrue(export_gate(plan, report)["ok"])

    def test_role_simulation_report_is_marked_and_lenient_only(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan, reviewer="role_simulation", no_counterexample=True)
        self.assertEqual(report["independence"], "role_simulation")
        lenient = export_gate(plan, report)
        self.assertTrue(lenient["ok"], lenient["reasons"])
        strict = export_gate(plan, report, strict_independence=True)
        self.assertFalse(strict["ok"])
        self.assertIn("严格模式要求独立子代理审校", strict["reasons"])

    def test_strict_independence_allows_native_report(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan, reviewer="native_subagent", no_counterexample=True)
        result = export_gate(plan, report, strict_independence=True)
        self.assertTrue(result["ok"], result["reasons"])

    def test_old_report_without_independence_falls_back_to_reviewer(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan, reviewer="native_subagent", no_counterexample=True)
        report.pop("independence", None)
        result = export_gate(plan, report, strict_independence=True)
        self.assertTrue(result["ok"], result["reasons"])

    def test_report_with_wrong_rubric_version_cannot_open_export_gate(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan)
        report["rubricVersion"] = "unsupported"
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertIn("审查量规版本不受支持", result["reasons"])

    def test_export_gate_rejects_report_with_unknown_status(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan)
        report["status"] = "invented_pass"
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertIn("审查报告状态无效", result["reasons"])

    def test_export_gate_rejects_unknown_finding_severity(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan)
        report["status"] = "needs_repair"
        report["findings"] = [{"id": "unknown-1", "severity": "critical", "status": "open"}]
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertIn("审查问题严重级别无效", result["reasons"])

    def test_export_gate_rejects_malformed_finding_without_crashing(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan)
        report["findings"] = [None]
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertIn("审查问题格式无效", result["reasons"])

    def test_export_gate_rejects_incomplete_forged_pass_report(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        forged = {
            "schemaVersion": REVIEW_SCHEMA_VERSION,
            "rubricVersion": RUBRIC_VERSION,
            "planHash": plan_hash(plan),
            "status": "passed",
        }
        result = export_gate(plan, forged)
        self.assertFalse(result["ok"])
        self.assertIn("审查报告缺少必要字段", result["reasons"])

    def test_export_gate_rejects_report_with_failed_structural_summary(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan)
        report["structuralValidation"] = {"ok": False, "issues": [{"path": "week"}]}
        result = export_gate(plan, report)
        self.assertFalse(result["ok"])
        self.assertIn("审查报告显示结构校验未通过", result["reasons"])

    def test_explicit_no_counterexample_opens_export_gate(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan, reviewer="native_subagent", no_counterexample=True)
        result = export_gate(plan, report)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["attestation"], "no_counterexample")
        self.assertTrue(result["ok"], result["reasons"])

    def test_gold_examples_can_export_after_no_counterexample_attestation(self) -> None:
        for path, plan in load_examples():
            report = adversarial_review(plan, reviewer="native_subagent", no_counterexample=True)
            result = export_gate(plan, report)
            self.assertEqual(report["status"], "passed", path.name)
            self.assertTrue(result["ok"], f"{path.name}: {result['reasons']}")

    def test_teacher_override_marks_passed_with_override(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan, reviewer="native_subagent")
        record_teacher_override(
            report, report["findings"][0]["id"],
            teacher="张老师", reason="本课先保留评分量表", plan=plan,
        )
        self.assertEqual(report["status"], "passed_with_override")
        self.assertTrue(export_gate(plan, report)["ok"], export_gate(plan, report)["reasons"])
