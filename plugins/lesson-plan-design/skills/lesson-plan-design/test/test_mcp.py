# -*- coding: utf-8 -*-
"""MCP 工具复用审查门禁与导出。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from support import PLUGIN_ROOT, load_mcp, utf8_env
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

    def test_mcp_handle_rejects_missing_required_argument(self) -> None:
        module = load_mcp("lesson_plan_mcp_missing_arg")
        reply = module.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "draft_lesson_plan", "arguments": {}},
        })
        self.assertEqual(reply["error"]["code"], -32602)
        self.assertEqual(reply["error"]["data"]["code"], "INVALID_PARAMS")
        self.assertTrue(
            any(item["path"] == "week" for item in reply["error"]["data"]["details"])
        )

    def test_mcp_handle_rejects_wrong_argument_type(self) -> None:
        module = load_mcp("lesson_plan_mcp_wrong_type")
        reply = module.handle({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {
                "name": "draft_lesson_plan",
                "arguments": {"week": "abc", "session": 1, "contentTitle": "测试课题"},
            },
        })
        self.assertEqual(reply["error"]["code"], -32602)
        details = reply["error"]["data"]["details"]
        self.assertTrue(any(item["path"] == "week" for item in details))

    def test_mcp_handle_unknown_tool(self) -> None:
        module = load_mcp("lesson_plan_mcp_unknown_tool")
        reply = module.handle({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "not_a_tool", "arguments": {}},
        })
        self.assertEqual(reply["error"]["code"], -32601)
        self.assertEqual(reply["error"]["data"]["code"], "METHOD_NOT_FOUND")

    def test_mcp_handle_contains_tool_exception(self) -> None:
        module = load_mcp("lesson_plan_mcp_tool_exception")
        original = module._dispatch_tool

        def boom(name, args):
            raise RuntimeError("boom")

        module._dispatch_tool = boom
        try:
            reply = module.handle({
                "jsonrpc": "2.0", "id": 4, "method": "tools/call",
                "params": {
                    "name": "draft_lesson_plan",
                    "arguments": {"week": 1, "session": 1, "contentTitle": "测试课题"},
                },
            })
        finally:
            module._dispatch_tool = original
        self.assertEqual(reply["error"]["code"], -32603)
        self.assertEqual(reply["error"]["data"]["code"], "TOOL_ERROR")

    def test_mcp_handle_valid_call_and_continues_after_error(self) -> None:
        module = load_mcp("lesson_plan_mcp_handle_valid")
        bad = module.handle({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "draft_lesson_plan", "arguments": {}},
        })
        good = module.handle({
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {
                "name": "draft_lesson_plan",
                "arguments": {"week": 1, "session": 1, "contentTitle": "测试课题"},
            },
        })
        ping = module.handle({"jsonrpc": "2.0", "id": 7, "method": "ping"})
        self.assertEqual(bad["error"]["code"], -32602)
        self.assertIn("result", good)
        payload = json.loads(good["result"]["content"][0]["text"])
        self.assertEqual(payload["plan"]["week"], 1)
        self.assertEqual(ping["result"], {})

    def test_mcp_main_reports_parse_error_and_keeps_running(self) -> None:
        script = PLUGIN_ROOT / "scripts" / "mcp_server.py"
        payload = "{bad\n" + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n"
        proc = subprocess.run(
            [sys.executable, str(script)],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=utf8_env(),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["error"]["code"], -32700)
        self.assertEqual(lines[0]["error"]["data"]["code"], "PARSE_ERROR")
        self.assertEqual(lines[1]["id"], 1)
        self.assertEqual(lines[1]["result"], {})
