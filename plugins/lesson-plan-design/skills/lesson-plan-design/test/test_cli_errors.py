# -*- coding: utf-8 -*-
"""CLI 契约：退出码、stdout/stderr 分离与统一 JSON 错误。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import SCRIPTS_DIR, utf8_env
from lib import draft_plan


def _run(script: str, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env or utf8_env(),
    )


class TestCliErrors(unittest.TestCase):
    def test_missing_arguments_return_usage_json(self) -> None:
        for script in (
            "validate.py",
            "draft.py",
            "adversarial_review.py",
            "export_docx.py",
            "score.py",
        ):
            proc = _run(script)
            self.assertEqual(proc.returncode, 2, script)
            self.assertEqual(proc.stdout, "", script)
            payload = json.loads(proc.stderr)
            self.assertEqual(payload["error"]["code"], "USAGE", script)
            self.assertTrue(payload["error"]["message"], script)
            self.assertTrue(payload["error"]["hint"], script)

    def test_invalid_json_returns_invalid_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{bad", encoding="utf-8")
            for script in ("validate.py", "score.py", "adversarial_review.py", "export_docx.py"):
                proc = _run(script, str(bad))
                self.assertEqual(proc.returncode, 1, script)
                self.assertEqual(proc.stdout, "", script)
                payload = json.loads(proc.stderr)
                self.assertEqual(payload["error"]["code"], "INVALID_JSON", script)

    def test_missing_file_returns_file_not_found(self) -> None:
        missing = str(Path(tempfile.gettempdir()) / "fr09-no-such-plan.json")
        for script in ("validate.py", "score.py", "adversarial_review.py", "export_docx.py"):
            proc = _run(script, missing)
            self.assertEqual(proc.returncode, 1, script)
            payload = json.loads(proc.stderr)
            self.assertEqual(payload["error"]["code"], "FILE_NOT_FOUND", script)

    def test_success_writes_result_to_stdout_only(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "教案.json"
            path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            proc = _run("validate.py", str(path))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])

    def test_gate_rejection_has_code_and_hint(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "教案.json"
            out = root / "教案.docx"
            path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            proc = _run("export_docx.py", str(path), "-o", str(out))
            self.assertEqual(proc.returncode, 1)
            self.assertFalse(out.exists())
            payload = json.loads(proc.stderr)
            self.assertEqual(payload["error"]["code"], "GATE_REJECTED")
            self.assertIn("缺少当前教案的对抗审查报告", payload["error"]["hint"])

    def test_error_does_not_echo_environment_secrets(self) -> None:
        env = utf8_env()
        env["LPP_SECRET"] = "super-secret-value"
        proc = _run("validate.py", str(Path(tempfile.gettempdir()) / "no-such.json"), env=env)
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("super-secret-value", proc.stderr + proc.stdout)

    def test_ten_failures_then_success(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root / "bad.json"
            bad.write_text("{bad", encoding="utf-8")
            for _ in range(10):
                proc = _run("validate.py", str(bad))
                self.assertEqual(proc.returncode, 1)
            good = root / "good.json"
            good.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            proc = _run("validate.py", str(good))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(json.loads(proc.stdout)["ok"])

    def test_help_goes_to_stdout_with_zero_exit(self) -> None:
        proc = _run("validate.py", "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("usage", proc.stdout.lower())
        self.assertEqual(proc.stderr, "")
