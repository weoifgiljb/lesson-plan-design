# -*- coding: utf-8 -*-
"""插件 session-start / stop hook。"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from support import PLUGIN_ROOT, tempdir, utf8_env
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
        with tempdir() as tmp:
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

    def _stop(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        script = PLUGIN_ROOT / "scripts" / "hook-stop.py"
        return subprocess.run(
            [sys.executable, str(script), "--root", str(root), *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=utf8_env(),
        )

    def test_stop_hook_finds_nested_plan(self) -> None:
        plan = draft_plan(1, 1, "嵌套课题")
        with tempdir() as tmp:
            nested = Path(tmp) / "周次" / "第1周"
            nested.mkdir(parents=True)
            (nested / "教案.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            proc = self._stop(Path(tmp))
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["count"], 1)
        self.assertTrue(payload["reports"][0]["file"].endswith("教案.json"))
        self.assertIn("第1周", payload["reports"][0]["file"])

    def test_stop_hook_strict_fails_on_missing_review(self) -> None:
        plan = draft_plan(1, 1, "严格课题")
        with tempdir() as tmp:
            (Path(tmp) / "教案.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            warned = self._stop(Path(tmp))
            strict = self._stop(Path(tmp), "--strict")
        self.assertEqual(json.loads(warned.stdout)["mode"], "warn")
        self.assertEqual(warned.returncode, 0)
        self.assertEqual(strict.returncode, 1)
        self.assertIn("缺少当前教案的对抗审查报告", strict.stdout)

    def test_stop_hook_checks_more_than_eight_plans(self) -> None:
        plan = draft_plan(1, 1, "批量课题")
        with tempdir() as tmp:
            for index in range(9):
                (Path(tmp) / f"教案{index}.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            proc = self._stop(Path(tmp))
        self.assertEqual(json.loads(proc.stdout)["count"], 9)

    def test_stop_hook_skips_noise_directories(self) -> None:
        plan = draft_plan(1, 1, "噪声课题")
        with tempdir() as tmp:
            for folder in ("node_modules", "output"):
                target = Path(tmp) / folder
                target.mkdir()
                (target / "教案.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            proc = self._stop(Path(tmp))
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["count"], 0)
        self.assertIn("未发现教案", payload["message"])

    def test_post_write_hook_reports_chinese_issues(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["knowledgeGoals"] = ""
        script = PLUGIN_ROOT / "scripts" / "hook-post-write.py"
        with tempdir() as tmp:
            target = Path(tmp) / "教案.json"
            target.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            payload = json.dumps({"tool_input": {"file_path": str(target)}}, ensure_ascii=False)
            proc = subprocess.run(
                [sys.executable, str(script)],
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=utf8_env(),
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("knowledgeGoals", proc.stdout)
        self.assertIn("不能为空", proc.stdout)
        self.assertNotIn("UnicodeDecodeError", proc.stderr)
