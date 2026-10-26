# -*- coding: utf-8 -*-
"""MCP 工具复用审查门禁与导出。"""
from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from support import load_mcp
from lib import adversarial_review, draft_plan


class TestMcp(unittest.TestCase):
    def test_mcp_export_reuses_review_gate(self) -> None:
        module = load_mcp("lesson_plan_mcp_test")
        plan = draft_plan(1, 1, "测试课题")
        response = json.loads(module.call_tool("export_lesson_docx", {"plan": plan})["content"][0]["text"])
        self.assertFalse(response["ok"])
        self.assertIn("缺少当前教案的对抗审查报告", response["reasons"])

    def test_mcp_rejects_non_object_review_report_without_crashing(self) -> None:
        module = load_mcp("lesson_plan_mcp_bad_report_test")
        plan = draft_plan(1, 1, "测试课题")
        response = json.loads(module.call_tool("export_lesson_docx", {"plan": plan, "reviewReport": "bad"})["content"][0]["text"])
        self.assertFalse(response["ok"])
        self.assertIn("审查报告格式无效", response["reasons"])

    def test_mcp_rejects_non_object_previous_report_without_crashing(self) -> None:
        module = load_mcp("lesson_plan_mcp_bad_previous_report_test")
        plan = draft_plan(1, 1, "测试课题")
        response = json.loads(module.call_tool("start_adversarial_review", {"plan": plan, "previousReport": "bad"})["content"][0]["text"])
        self.assertFalse(response["ok"])
        self.assertIn("previousReport", response["error"])

    def test_mcp_read_review_valid_matches_export_gate(self) -> None:
        module = load_mcp("lesson_plan_mcp_read_test")
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan)
        response = json.loads(module.call_tool("read_lesson_review", {"plan": plan, "reviewReport": report})["content"][0]["text"])
        self.assertFalse(response["gate"]["ok"])
        self.assertFalse(response["valid"])

    def test_mcp_teacher_override_rejects_malformed_overrides_without_crashing(self) -> None:
        module = load_mcp("lesson_plan_mcp_bad_override_test")
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan, reviewer="native_subagent")
        report["overrides"] = {}
        response = json.loads(module.call_tool("record_teacher_override", {
            "plan": plan,
            "reviewReport": report,
            "issueId": report["findings"][0]["id"],
            "teacher": "张老师",
            "reason": "保留当前评分量表",
        })["content"][0]["text"])
        self.assertFalse(response["ok"])
        self.assertIn("审查放行记录格式无效", response["error"])

    def test_mcp_review_without_attestation_cannot_export(self) -> None:
        module = load_mcp("lesson_plan_mcp_pending_export")
        plan = draft_plan(1, 1, "测试课题")
        started = json.loads(module.call_tool("start_adversarial_review", {
            "plan": plan, "reviewerMode": "native_subagent",
        })["content"][0]["text"])
        exported = json.loads(module.call_tool("export_lesson_docx", {
            "plan": plan, "reviewReport": started,
        })["content"][0]["text"])
        self.assertEqual(started["status"], "pending_reviewer")
        self.assertFalse(exported["ok"])

    def test_mcp_attested_review_then_export_writes_docx(self) -> None:
        module = load_mcp("lesson_plan_mcp_export_success")
        plan = draft_plan(1, 1, "测试课题")
        started = json.loads(module.call_tool("start_adversarial_review", {
            "plan": plan,
            "reviewerMode": "native_subagent",
            "noCounterexample": True,
        })["content"][0]["text"])
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "exported.docx"
            exported = json.loads(module.call_tool("export_lesson_docx", {
                "plan": plan,
                "reviewReport": started,
                "outputPath": str(output_path),
            })["content"][0]["text"])
            self.assertEqual(started["status"], "passed")
            self.assertTrue(exported["ok"], exported)
            self.assertTrue(output_path.is_file())

    def test_mcp_export_embeds_relative_media_with_base_dir(self) -> None:
        module = load_mcp("lesson_plan_mcp_export_media")
        plan = draft_plan(1, 1, "测试课题")
        plan["mediaAssets"] = [
            {"path": "page-003.png", "caption": "教材第3页", "attachTo": "knowledgeLearning"}
        ]
        started = json.loads(module.call_tool("start_adversarial_review", {
            "plan": plan,
            "reviewerMode": "native_subagent",
            "noCounterexample": True,
        })["content"][0]["text"])
        png_bytes = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
        )
        with tempfile.TemporaryDirectory() as tmp:
            lesson_dir = Path(tmp)
            (lesson_dir / "page-003.png").write_bytes(png_bytes)
            output_path = lesson_dir / "exported.docx"
            exported = json.loads(module.call_tool("export_lesson_docx", {
                "plan": plan,
                "reviewReport": started,
                "outputPath": str(output_path),
                "baseDir": str(lesson_dir),
            })["content"][0]["text"])
            self.assertTrue(exported["ok"], exported)
            with zipfile.ZipFile(output_path) as zf:
                names = zf.namelist()
                rels = zf.read("word/_rels/document.xml.rels").decode("utf-8")
            self.assertTrue(any(name.startswith("word/media/") for name in names), names)
            self.assertIn("/image", rels)

    def test_mcp_teacher_override_requires_matching_plan(self) -> None:
        module = load_mcp("lesson_plan_mcp_override_plan")
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        report = adversarial_review(plan, reviewer="native_subagent")
        missing_plan = json.loads(module.call_tool("record_teacher_override", {
            "reviewReport": report,
            "issueId": report["findings"][0]["id"],
            "teacher": "张老师",
            "reason": "保留当前评分量表",
        })["content"][0]["text"])
        stale = dict(plan)
        stale["activityFlow"] = dict(plan["activityFlow"])
        stale["activityFlow"]["summary"] = "已改小结"
        mismatched = json.loads(module.call_tool("record_teacher_override", {
            "reviewReport": report,
            "issueId": report["findings"][0]["id"],
            "teacher": "张老师",
            "reason": "保留当前评分量表",
            "plan": stale,
        })["content"][0]["text"])
        self.assertFalse(missing_plan["ok"])
        self.assertIn("教案", missing_plan["error"])
        self.assertFalse(mismatched["ok"])
        self.assertIn("不匹配", mismatched["error"])

    def test_mcp_validate_strict_catalog_conflict(self) -> None:
        module = load_mcp("lesson_plan_mcp_validate_strict")
        plan = draft_plan(2, 1, "一级考证辅导2", content_detail="第1、2套")
        default = json.loads(
            module.call_tool("validate_lesson_plan", {"plan": plan})["content"][0]["text"]
        )
        strict = json.loads(
            module.call_tool("validate_lesson_plan", {"plan": plan, "strict": True})["content"][0]["text"]
        )
        self.assertTrue(default["ok"], default)
        self.assertFalse(strict["ok"])
        self.assertEqual(strict["ruleVersion"], "1.1.0")
