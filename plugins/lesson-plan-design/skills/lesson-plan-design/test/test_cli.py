# -*- coding: utf-8 -*-
"""校验 / 审查 / 导出 CLI 与插件根转发脚本。"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from support import PLUGIN_ROOT, tempdir
from export_docx import ENGINE_VERSION, export_docx
from lib import default_review_path, load_review_report, plan_hash
from factories import make_plan, read_docx_xml, run_cli, write_plan, write_report


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = Path(self._tmp.__enter__())
        self.addCleanup(self._tmp.__exit__, None, None, None)

    def _plan_file(self, plan: dict, name: str = "教案.json") -> Path:
        return write_plan(self.root, plan, name)

    def test_export_docx(self) -> None:
        plan = make_plan(1, 2, "一级考证辅导1")
        out = self.root / "demo.docx"
        self.assertGreater(export_docx(plan, out).stat().st_size, 1000)

    def test_cli_export_requires_current_review_report(self) -> None:
        plan = make_plan()
        plan_path = self._plan_file(plan)
        output_path = self.root / "blocked.docx"
        denied = run_cli("export_docx.py", plan_path, "-o", output_path)
        self.assertNotEqual(denied.returncode, 0)
        self.assertFalse(output_path.exists())
        write_report(plan_path, plan)
        exported = run_cli("export_docx.py", plan_path)
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertTrue((self.root / "教案_第1周第1次.docx").is_file())
        payload = json.loads(exported.stdout)
        self.assertEqual(payload["engineVersion"], ENGINE_VERSION)
        self.assertTrue(payload["selfCheck"]["ok"], payload["selfCheck"])

    def test_review_cli_persists_current_report_for_export(self) -> None:
        plan = make_plan()
        plan_path = self._plan_file(plan)
        reviewed = run_cli("adversarial_review.py", plan_path, "--no-counterexample")
        self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
        report = load_review_report(default_review_path(plan_path))
        self.assertEqual(report["planHash"], plan_hash(plan))
        self.assertEqual(report["status"], "passed")

    def test_review_cli_returns_nonzero_for_needs_repair(self) -> None:
        plan = make_plan()
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        plan_path = self._plan_file(plan)
        reviewed = run_cli(
            "adversarial_review.py", plan_path, "--reviewer-mode", "native_subagent",
        )
        self.assertNotEqual(reviewed.returncode, 0)

    def test_cli_teacher_override_rejects_stale_plan(self) -> None:
        plan = make_plan()
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        plan_path = self._plan_file(plan)
        run_cli("adversarial_review.py", plan_path)
        report = load_review_report(default_review_path(plan_path))
        plan["activityFlow"]["summary"] = "已改课堂小结"
        self._plan_file(plan)
        overridden = run_cli(
            "adversarial_review.py", plan_path,
            "--override", report["findings"][0]["id"],
            "--teacher", "张老师", "--reason", "本课先保留评分量表",
        )
        combined = overridden.stderr + overridden.stdout
        self.assertNotEqual(overridden.returncode, 0)
        self.assertIn("不匹配", combined)

    def test_cli_override_strict_teacher(self) -> None:
        plan = make_plan(title="教师一致", teacher="张老师")
        plan["activityFlow"]["assessment"] = "过程考核：30\n结果考核：70"
        plan_path = self._plan_file(plan)
        report = write_report(plan_path, plan)
        denied = run_cli(
            "adversarial_review.py", plan_path,
            "--override", report["findings"][0]["id"],
            "--teacher", "李老师", "--reason", "本课先保留评分量表",
            "--strict-teacher",
        )
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("不一致", denied.stderr + denied.stdout)
        allowed = run_cli(
            "adversarial_review.py", plan_path,
            "--override", report["findings"][0]["id"],
            "--teacher", "张老师", "--reason", "本课先保留评分量表",
            "--strict-teacher",
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr + allowed.stdout)
        self.assertEqual(len(load_review_report(default_review_path(plan_path))["overrides"]), 1)

    def test_cli_export_reports_unreadable_review_file(self) -> None:
        plan_path = self._plan_file(make_plan())
        default_review_path(plan_path).write_text("{not-json", encoding="utf-8")
        denied = run_cli("export_docx.py", plan_path, "-o", self.root / "blocked.docx")
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
        plan = make_plan(2, 1, "一级考证辅导2", content_detail="第1、2套")
        payload = json.dumps(plan, ensure_ascii=False)
        default = run_cli("validate.py", "--stdin", input_text=payload)
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertIn("warnings", default.stdout)
        strict = run_cli("validate.py", "--stdin", "--strict", input_text=payload)
        self.assertNotEqual(strict.returncode, 0)

    def test_cli_validate_minutes_tolerance(self) -> None:
        plan = make_plan()
        tolerance = 5
        expected = plan["plannedHours"] * 45
        plan["activityFlow"]["introduction"] = [
            {"mainContent": "导入", "minutes": expected + tolerance}
        ]
        payload = json.dumps(plan, ensure_ascii=False)
        denied = run_cli("validate.py", "--stdin", input_text=payload)
        self.assertNotEqual(denied.returncode, 0)
        allowed = run_cli(
            "validate.py", "--stdin", "--minutes-tolerance", tolerance, input_text=payload,
        )
        self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)

    def test_export_marks_role_simulation(self) -> None:
        plan = make_plan(2, 1, "一级考证辅导2", content_detail="第3、4套")
        out = self.root / "marked.docx"
        export_docx(plan, out, independence="role_simulation")
        self.assertIn("审校方式：角色模拟", read_docx_xml(out))

    def test_cli_export_strict_independence(self) -> None:
        plan = make_plan(2, 1, "一级考证辅导2", content_detail="第3、4套")
        plan_path = self._plan_file(plan)
        out = self.root / "strict.docx"
        write_report(plan_path, plan, reviewer="role_simulation")
        denied = run_cli(
            "export_docx.py", plan_path, "--strict-independence", "-o", out,
        )
        self.assertNotEqual(denied.returncode, 0)
        self.assertFalse(out.exists())
        self.assertIn("严格模式要求独立子代理审校", denied.stderr + denied.stdout)
        write_report(plan_path, plan, reviewer="native_subagent")
        allowed = run_cli(
            "export_docx.py", plan_path, "--strict-independence", "-o", out,
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr + allowed.stdout)
        self.assertTrue(out.exists())

    def test_export_includes_metadata_and_normalized_hours(self) -> None:
        plan = make_plan(2, 1, "一级考证辅导2", content_detail="第3、4套")
        plan.update({
            "school": "东莞经贸学校",
            "planNumber": "IT-0201",
            "teachDate": "2026-10-26",
            "teacher": "张老师",
            "teachingObject": "计算机2301",
            "plannedHours": 2.0,
        })
        out = self.root / "meta.docx"
        export_docx(plan, out)
        xml = read_docx_xml(out)
        for value in ("东莞经贸学校", "IT-0201", "2026-10-26", "张老师", "计算机2301"):
            self.assertIn(value, xml)
        self.assertNotIn("2.0", xml)

    def test_export_strict_metadata_rejects_empty_teacher(self) -> None:
        plan = make_plan(2, 1, "一级考证辅导2", content_detail="第3、4套")
        plan["teacher"] = ""
        plan["teachingObject"] = "计算机2301"
        plan["teachDate"] = "2026-10-26"
        out = self.root / "strict.docx"
        with self.assertRaises(ValueError):
            export_docx(plan, out, strict_metadata=True)
        self.assertFalse(out.exists())

    def test_cli_export_strict_metadata(self) -> None:
        plan = make_plan(2, 1, "一级考证辅导2", content_detail="第3、4套")
        plan["teacher"] = ""
        plan["teachingObject"] = "计算机2301"
        plan["teachDate"] = "2026-10-26"
        plan_path = self._plan_file(plan)
        out = self.root / "strict.docx"
        write_report(plan_path, plan)
        denied = run_cli("export_docx.py", plan_path, "--strict-metadata", "-o", out)
        self.assertNotEqual(denied.returncode, 0)
        self.assertFalse(out.exists())
        self.assertIn("严格模式缺少元信息", denied.stderr + denied.stdout)
        plan["teacher"] = "张老师"
        self._plan_file(plan)
        write_report(plan_path, plan)
        allowed = run_cli("export_docx.py", plan_path, "--strict-metadata", "-o", out)
        self.assertEqual(allowed.returncode, 0, allowed.stderr + allowed.stdout)
        self.assertTrue(out.exists())
