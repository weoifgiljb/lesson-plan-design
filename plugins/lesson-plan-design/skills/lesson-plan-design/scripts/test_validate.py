# -*- coding: utf-8 -*-
"""教案校验与草稿的单元测试。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_docx import export_docx
from lib import (
    REVIEW_SCHEMA_VERSION,
    RUBRIC_VERSION,
    adversarial_review,
    default_review_path,
    draft_plan,
    export_gate,
    load_review_report,
    load_examples,
    plan_hash,
    record_teacher_override,
    save_review_report,
    score_against_examples,
    validate_plan,
)


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

        record_teacher_override(report, issue_id, teacher="张老师", reason="本课先保留评分量表")
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

    def test_role_simulation_report_can_open_export_gate(self) -> None:
        plan = draft_plan(1, 1, "测试课题")

        result = export_gate(plan, adversarial_review(plan, reviewer="role_simulation"))

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

    def test_cli_export_requires_current_review_report(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "教案.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            script = Path(__file__).with_name("export_docx.py")
            output_path = root / "blocked.docx"

            denied = subprocess.run([sys.executable, str(script), str(plan_path), "-o", str(output_path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(denied.returncode, 0)
            self.assertFalse(output_path.exists())

            save_review_report(default_review_path(plan_path), adversarial_review(plan, reviewer="native_subagent"))
            exported = subprocess.run([sys.executable, str(script), str(plan_path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(exported.returncode, 0, exported.stderr)
            self.assertTrue((root / "教案_第1周第1次.docx").is_file())

    def test_review_cli_persists_current_report_for_export(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "教案.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            review_script = Path(__file__).with_name("adversarial_review.py")

            reviewed = subprocess.run(
                [sys.executable, str(review_script), str(plan_path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )

            self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
            report = load_review_report(default_review_path(plan_path))
            self.assertEqual(report["planHash"], plan_hash(plan))
            self.assertEqual(report["status"], "passed")

    def test_review_cli_returns_nonzero_for_needs_repair(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "教案.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            review_script = Path(__file__).with_name("adversarial_review.py")

            reviewed = subprocess.run(
                [sys.executable, str(review_script), str(plan_path), "--reviewer-mode", "native_subagent"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )

            self.assertNotEqual(reviewed.returncode, 0)

    def test_mcp_export_reuses_review_gate(self) -> None:
        plugin_root = Path(__file__).resolve().parents[3]
        mcp_path = plugin_root / "scripts" / "mcp_server.py"
        sys.path.insert(0, str(mcp_path.parent))
        spec = importlib.util.spec_from_file_location("lesson_plan_mcp_test", mcp_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        plan = draft_plan(1, 1, "测试课题")

        response = json.loads(module.call_tool("export_lesson_docx", {"plan": plan})["content"][0]["text"])

        self.assertFalse(response["ok"])
        self.assertIn("缺少当前教案的对抗审查报告", response["reasons"])

    def test_mcp_rejects_non_object_review_report_without_crashing(self) -> None:
        plugin_root = Path(__file__).resolve().parents[3]
        mcp_path = plugin_root / "scripts" / "mcp_server.py"
        sys.path.insert(0, str(mcp_path.parent))
        spec = importlib.util.spec_from_file_location("lesson_plan_mcp_bad_report_test", mcp_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        plan = draft_plan(1, 1, "测试课题")

        response = json.loads(module.call_tool("export_lesson_docx", {"plan": plan, "reviewReport": "bad"})["content"][0]["text"])

        self.assertFalse(response["ok"])
        self.assertIn("审查报告格式无效", response["reasons"])

    def test_mcp_rejects_non_object_previous_report_without_crashing(self) -> None:
        plugin_root = Path(__file__).resolve().parents[3]
        mcp_path = plugin_root / "scripts" / "mcp_server.py"
        sys.path.insert(0, str(mcp_path.parent))
        spec = importlib.util.spec_from_file_location("lesson_plan_mcp_bad_previous_report_test", mcp_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        plan = draft_plan(1, 1, "测试课题")

        response = json.loads(module.call_tool("start_adversarial_review", {"plan": plan, "previousReport": "bad"})["content"][0]["text"])

        self.assertFalse(response["ok"])
        self.assertIn("previousReport", response["error"])

    def test_mcp_read_review_valid_matches_export_gate(self) -> None:
        plugin_root = Path(__file__).resolve().parents[3]
        mcp_path = plugin_root / "scripts" / "mcp_server.py"
        sys.path.insert(0, str(mcp_path.parent))
        spec = importlib.util.spec_from_file_location("lesson_plan_mcp_read_test", mcp_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan)

        response = json.loads(module.call_tool("read_lesson_review", {"plan": plan, "reviewReport": report})["content"][0]["text"])

        self.assertFalse(response["gate"]["ok"])
        self.assertFalse(response["valid"])

    def test_mcp_teacher_override_rejects_malformed_overrides_without_crashing(self) -> None:
        plugin_root = Path(__file__).resolve().parents[3]
        mcp_path = plugin_root / "scripts" / "mcp_server.py"
        sys.path.insert(0, str(mcp_path.parent))
        spec = importlib.util.spec_from_file_location("lesson_plan_mcp_bad_override_test", mcp_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan, reviewer="native_subagent")
        report["overrides"] = {}

        response = json.loads(module.call_tool("record_teacher_override", {
            "reviewReport": report,
            "issueId": report["findings"][0]["id"],
            "teacher": "张老师",
            "reason": "保留当前评分量表",
        })["content"][0]["text"])

        self.assertFalse(response["ok"])
        self.assertIn("审查放行记录格式无效", response["error"])


if __name__ == "__main__":
    unittest.main()
