# -*- coding: utf-8 -*-
"""FR-16 一键流程、字段级修订与两版差异。"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from factories import make_plan, run_cli, write_plan, write_report
from support import tempdir


class TestWorkflow(unittest.TestCase):
    def test_flow_until_validate_then_resume_export(self) -> None:
        with tempdir() as tmp:
            root = Path(tmp)
            partial = run_cli(
                "lesson_flow.py", "--week", "1", "--session", "1", "--title", "流程课题",
                "--out-dir", root, "--until", "validate",
            )
            self.assertEqual(partial.returncode, 0, partial.stderr)
            plan_path = root / "教案_流程课题_第1周第1次.json"
            self.assertTrue(plan_path.is_file())
            self.assertFalse((root / "教案_流程课题_第1周第1次.review.json").exists())

            full = run_cli(
                "lesson_flow.py", "--plan", plan_path, "--until", "export",
            )
            self.assertEqual(full.returncode, 0, full.stderr)
            payload = json.loads(full.stdout)
            self.assertTrue(Path(payload["docx"]).is_file())
            self.assertTrue(Path(payload["review"]).is_file())

    def test_revise_warns_old_report_and_updates_field(self) -> None:
        plan = make_plan(1, 1, "修订前")
        with tempdir() as tmp:
            plan_path = write_plan(Path(tmp), plan)
            write_report(plan_path, plan)
            revised = run_cli("revise_plan.py", plan_path, "--set", "contentTitle=修订后")
            self.assertEqual(revised.returncode, 0, revised.stderr)
            payload = json.loads(revised.stdout)
            self.assertTrue(payload["reviewInvalidated"])
            self.assertIn("旧审查报告已失效", "；".join(payload["warnings"]))
            self.assertEqual(json.loads(plan_path.read_text(encoding="utf-8"))["contentTitle"], "修订后")
            reviewed = run_cli("adversarial_review.py", plan_path, "--no-counterexample")
            self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
            exported = run_cli("export_docx.py", plan_path, "-o", Path(tmp) / "revised.docx")
            self.assertEqual(exported.returncode, 0, exported.stderr)

    def test_revise_rejects_unknown_path_without_touching_file(self) -> None:
        plan = make_plan(1, 1, "原子性")
        with tempdir() as tmp:
            plan_path = write_plan(Path(tmp), plan)
            before = plan_path.read_bytes()
            proc = run_cli("revise_plan.py", plan_path, "--set", "noSuchField=1")
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(plan_path.read_bytes(), before)
            self.assertIn("INVALID_PATH", proc.stdout + proc.stderr)

    def test_diff_plans_reports_changed_paths(self) -> None:
        plan = make_plan(1, 1, "差异前")
        with tempdir() as tmp:
            left = write_plan(Path(tmp), plan, "left.json")
            plan["contentTitle"] = "差异后"
            right = write_plan(Path(tmp), plan, "right.json")
            proc = run_cli("diff_plans.py", left, right)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["changes"][0]["path"], "contentTitle")


if __name__ == "__main__":
    unittest.main()
