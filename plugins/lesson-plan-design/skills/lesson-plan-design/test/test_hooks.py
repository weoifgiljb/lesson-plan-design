# -*- coding: utf-8 -*-
"""插件 session-start / stop hook。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import PLUGIN_ROOT, utf8_env
from lib import draft_plan


class TestHooks(unittest.TestCase):
    def test_session_start_mentions_review_report_gate(self) -> None:
        script = PLUGIN_ROOT / "scripts" / "session-start.py"
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=utf8_env(),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(".review.json", proc.stdout)
        self.assertIn("validate.py", proc.stdout)

    def test_stop_hook_notes_missing_review_report(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        script = PLUGIN_ROOT / "scripts" / "hook-stop.py"
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "教案.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(script)],
                cwd=tmp,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=utf8_env(),
            )
        payload = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(any(item.get("review") for item in payload["reports"]))
