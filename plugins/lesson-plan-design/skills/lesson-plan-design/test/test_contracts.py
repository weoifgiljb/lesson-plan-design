# -*- coding: utf-8 -*-
"""报告与 fixtures 契约的静态校验。"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from support import SKILL_DIR
from lib import adversarial_review, draft_plan

ROOT = SKILL_DIR.parents[3]
EXPECTED = ROOT / "tests" / "fixtures" / "dual-end" / "expected.json"


class TestContracts(unittest.TestCase):
    def test_review_report_has_required_contract_fields(self) -> None:
        report = adversarial_review(draft_plan(1, 1, "契约检查"), no_counterexample=True)
        for key in (
            "schemaVersion", "rubricVersion", "planHash", "round", "reviewer",
            "reviewedAt", "structuralValidation", "findings", "overrides",
            "repairHistory", "attestation", "status",
        ):
            self.assertIn(key, report)
        self.assertIn(report["status"], {
            "structure_invalid", "pending_reviewer", "needs_repair", "passed", "passed_with_override",
        })

    def test_dual_end_expected_fixtures_are_well_formed(self) -> None:
        data = json.loads(EXPECTED.read_text(encoding="utf-8"))
        self.assertIn("plugin", data)
        self.assertIn("platform", data)
        self.assertIn("stale_report", data)
        for name, entry in data["plugin"].items():
            self.assertIn("target_ok", entry, name)
        for name, entry in data["platform"].items():
            self.assertIn("target_status", entry, name)
        self.assertTrue((ROOT / "tests" / "fixtures" / "dual-end" / "platform" / "packages").is_dir())
