# -*- coding: utf-8 -*-
"""校验 / 审查 / 导出 CLI 与插件根转发脚本。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import PLUGIN_ROOT, SCRIPTS_DIR, utf8_env
from export_docx import export_docx
from lib import (
    adversarial_review,
    default_review_path,
    draft_plan,
    load_review_report,
    plan_hash,
    save_review_report,
)


class TestCli(unittest.TestCase):
    def test_export_docx(self) -> None:
        plan = draft_plan(1, 2, "一级考证辅导1")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "demo.docx"
            saved = export_docx(plan, out)
            self.assertGreater(saved.stat().st_size, 1000)

    def test_cli_export_requires_current_review_report(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "教案.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            script = SCRIPTS_DIR / "export_docx.py"
            output_path = root / "blocked.docx"
            denied = subprocess.run(
                [sys.executable, str(script), str(plan_path), "-o", str(output_path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertNotEqual(denied.returncode, 0)
            self.assertFalse(output_path.exists())
            save_review_report(
                default_review_path(plan_path),
                adversarial_review(plan, reviewer="native_subagent", no_counterexample=True),
            )
            exported = subprocess.run(
                [sys.executable, str(script), str(plan_path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(exported.returncode, 0, exported.stderr)
            self.assertTrue((root / "教案_第1周第1次.docx").is_file())

    def test_review_cli_persists_current_report_for_export(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "教案.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            review_script = SCRIPTS_DIR / "adversarial_review.py"
            reviewed = subprocess.run(
                [sys.executable, str(review_script), str(plan_path), "--no-counterexample"],
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
            review_script = SCRIPTS_DIR / "adversarial_review.py"
            reviewed = subprocess.run(
                [sys.executable, str(review_script), str(plan_path), "--reviewer-mode", "native_subagent"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertNotEqual(reviewed.returncode, 0)

    def test_cli_teacher_override_rejects_stale_plan(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "教案.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            review_script = SCRIPTS_DIR / "adversarial_review.py"
            subprocess.run(
                [sys.executable, str(review_script), str(plan_path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=utf8_env(),
            )
            report = load_review_report(default_review_path(plan_path))
            plan["activityFlow"]["summary"] = "已改课堂小结"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            overridden = subprocess.run(
                [
                    sys.executable, str(review_script), str(plan_path),
                    "--override", report["findings"][0]["id"],
                    "--teacher", "张老师", "--reason", "本课先保留评分量表",
                ],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=utf8_env(),
            )
            combined = overridden.stderr + overridden.stdout
            self.assertNotEqual(overridden.returncode, 0)
            self.assertIn("不匹配", combined)

    def test_cli_export_reports_unreadable_review_file(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "教案.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            default_review_path(plan_path).write_text("{not-json", encoding="utf-8")
            script = SCRIPTS_DIR / "export_docx.py"
            denied = subprocess.run(
                [sys.executable, str(script), str(plan_path), "-o", str(root / "blocked.docx")],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=utf8_env(),
            )
            combined = denied.stderr + denied.stdout
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn("无法解析", combined)
            self.assertNotIn("缺少当前教案的对抗审查报告", combined)

    def test_plugin_root_has_adversarial_review_forwarder(self) -> None:
        script = PLUGIN_ROOT / "scripts" / "adversarial_review.py"
        self.assertTrue(script.is_file(), script)
        proc = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("no-counterexample", proc.stdout)

    def test_cli_validate_strict_catalog_conflict(self) -> None:
        plan = draft_plan(2, 1, "一级考证辅导2", content_detail="第1、2套")
        script = SCRIPTS_DIR / "validate.py"
        payload = json.dumps(plan, ensure_ascii=False)
        default = subprocess.run(
            [sys.executable, str(script), "--stdin"],
            input=payload,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=utf8_env(),
        )
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertIn("warnings", default.stdout)
        strict = subprocess.run(
            [sys.executable, str(script), "--stdin", "--strict"],
            input=payload,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=utf8_env(),
        )
        self.assertNotEqual(strict.returncode, 0)

    def test_cli_validate_minutes_tolerance(self) -> None:
        plan = draft_plan(1, 1, "测试课题")
        plan["activityFlow"]["introduction"] = [{"mainContent": "导入", "minutes": 95}]
        script = SCRIPTS_DIR / "validate.py"
        payload = json.dumps(plan, ensure_ascii=False)
        denied = subprocess.run(
            [sys.executable, str(script), "--stdin"],
            input=payload,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=utf8_env(),
        )
        self.assertNotEqual(denied.returncode, 0)
        allowed = subprocess.run(
            [sys.executable, str(script), "--stdin", "--minutes-tolerance", "5"],
            input=payload,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=utf8_env(),
        )
        self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)
