# -*- coding: utf-8 -*-
"""对抗审查：预检、反例与报告落盘。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import SKILL_DIR  # noqa: F401
from lib import (
    REVIEW_SCHEMA_VERSION,
    RUBRIC_VERSION,
    adversarial_review,
    default_review_path,
    draft_plan,
    export_gate,
    load_examples,
    load_review_report,
    plan_hash,
    save_review_report,
)


class TestReview(unittest.TestCase):
    def test_gold_examples_do_not_trigger_preflight_findings(self) -> None:
        items = load_examples()
        self.assertEqual(len(items), 7)
        for path, plan in items:
            report = adversarial_review(plan)
            hypotheses = [item.get("hypothesis") for item in report.get("findings", [])]
            self.assertNotIn("task_not_executable", hypotheses, path.name)
            self.assertNotIn("assessment_cannot_prove_learning", hypotheses, path.name)

    def test_invalid_plan_does_not_enter_adversarial_review(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["knowledgeGoals"] = ""
        report = adversarial_review(plan)
        self.assertEqual(report["status"], "structure_invalid")
        self.assertEqual(report["findings"], [])
        self.assertFalse(report["structuralValidation"]["ok"])

    def test_adversarial_review_exposes_assessment_that_cannot_prove_learning(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan, round_number=2)
        self.assertEqual(report["schemaVersion"], REVIEW_SCHEMA_VERSION)
        self.assertEqual(report["round"], 2)
        self.assertEqual(report["planHash"], plan_hash(plan))
        self.assertEqual(len(report["findings"]), 1)
        finding = report["findings"][0]
        self.assertEqual(finding["hypothesis"], "assessment_cannot_prove_learning")
        self.assertEqual(finding["severity"], "major")
        self.assertEqual(finding["affectedPaths"], ["activityFlow.assessment"])
        self.assertEqual(finding["status"], "open")

    def test_external_finding_cannot_bypass_stronger_preflight_finding(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(
            plan,
            finding={
                "severity": "minor",
                "hypothesis": "cosmetic_issue",
                "evidence": ["课堂小结可以更具体。"],
                "affectedPaths": ["activityFlow.summary"],
                "whyItBreaksTheLoop": "反馈证据较弱。",
                "minimalRepair": "补充一项回顾问题。",
            },
        )
        self.assertEqual(report["findings"][0]["hypothesis"], "assessment_cannot_prove_learning")
        self.assertEqual(report["findings"][0]["severity"], "major")

    def test_adversarial_review_exposes_task_without_verifiable_output(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["taskImplementation"] = "1、必须完成：完成第21套\n2、选做：第1套"
        report = adversarial_review(plan)
        self.assertEqual(report["findings"][0]["hypothesis"], "task_not_executable")
        self.assertEqual(report["findings"][0]["severity"], "major")

    def test_adversarial_review_accepts_one_agent_reported_goal_activity_counterexample(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(
            plan,
            finding={
                "severity": "blocker",
                "hypothesis": "goal_activity_misalignment",
                "evidence": ["abilityGoals: 独立完成电子表格操作", "activityFlow.knowledgeLearning: 教师讲授步骤"],
                "affectedPaths": ["abilityGoals", "activityFlow.knowledgeLearning"],
                "whyItBreaksTheLoop": "没有学生练习活动，能力目标无法在课堂内达成。",
                "minimalRepair": "在任务实施中增加与能力目标对应的学生操作和提交物。",
            },
            reviewer="native_subagent",
        )
        finding = report["findings"][0]
        self.assertEqual(finding["hypothesis"], "goal_activity_misalignment")
        self.assertEqual(finding["severity"], "blocker")
        self.assertEqual(report["reviewer"], "native_subagent")

    def test_new_blocking_finding_cannot_claim_to_be_closed(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(
            plan,
            finding={
                "severity": "major",
                "hypothesis": "unverifiable_assessment",
                "evidence": ["assessment lacks observable evidence"],
                "affectedPaths": ["activityFlow.assessment"],
                "whyItBreaksTheLoop": "目标无法被核验。",
                "minimalRepair": "补充可观察的评分证据。",
                "status": "closed",
            },
        )
        self.assertEqual(report["findings"][0]["status"], "open")
        self.assertFalse(export_gate(plan, report)["ok"])

    def test_adversarial_review_rejects_non_list_finding_fields(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        with self.assertRaises(ValueError):
            adversarial_review(
                plan,
                finding={
                    "severity": "minor",
                    "hypothesis": "bad_shape",
                    "evidence": "not-a-list",
                    "affectedPaths": ["activityFlow.assessment"],
                    "whyItBreaksTheLoop": "格式错误",
                    "minimalRepair": "修正格式",
                },
            )

    def test_review_without_finding_or_attestation_is_pending(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        report = adversarial_review(plan, reviewer="native_subagent")
        result = export_gate(plan, report)
        self.assertEqual(report["status"], "pending_reviewer")
        self.assertFalse(result["ok"])
        self.assertTrue(any("尚未完成" in reason for reason in result["reasons"]))

    def test_finding_ids_differ_across_plans(self) -> None:
        first = draft_plan(1, 1, "课题甲")
        second = draft_plan(1, 2, "课题乙")
        first["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        second["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        first_id = adversarial_review(first)["findings"][0]["id"]
        second_id = adversarial_review(second)["findings"][0]["id"]
        self.assertNotEqual(first_id, second_id)

    def test_report_is_saved_next_to_plan_and_keeps_previous_round_history(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        with tempfile.TemporaryDirectory() as tmp:
            plan_path = Path(tmp) / "教案.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            old_report = adversarial_review(plan, round_number=1)
            report_path = default_review_path(plan_path)
            save_review_report(report_path, old_report)
            plan["activityFlow"]["assessment"] = "依据学生提交的文件和现场操作记录评分。"
            new_report = adversarial_review(plan, round_number=2, previous_report=load_review_report(report_path))
            save_review_report(report_path, new_report)
            stored = load_review_report(report_path)
            self.assertEqual(report_path.name, "教案.review.json")
            self.assertEqual(stored["rubricVersion"], RUBRIC_VERSION)
            self.assertEqual(stored["repairHistory"][0]["round"], 1)
            self.assertEqual(stored["planHash"], plan_hash(plan))
