# -*- coding: utf-8 -*-
"""入库复校规则：6 个黄金包的目标错误码与关键负例。"""
from __future__ import annotations

import copy
import json
import unittest

from factories import build_package
from support import expected_platform, load_json_bytes, plugin_report, read_package_dir

from app.adapters import engine
from app.domain import ingest, manifest as manifest_rules


def evaluate(files: dict[str, bytes], *, previous_round: int = 0):
    manifest = load_json_bytes(files["manifest.json"])
    plan = load_json_bytes(files["plan.json"])
    report = load_json_bytes(files["plan.review.json"])
    snapshot = report.get("planSnapshot")
    return ingest.evaluate(
        manifest=manifest,
        files=files,
        plan=plan,
        report=report,
        report_sha256=manifest_rules.sha256_bytes(files["plan.review.json"]),
        plan_hash=engine.plan_hash(plan),
        snapshot_hash=engine.plan_hash(snapshot) if isinstance(snapshot, dict) else None,
        previous_round=previous_round,
        validation=engine.validate_plan(plan),
    )


class TestIngestVerdicts(unittest.TestCase):
    def test_fixture_packages_match_expected_codes(self) -> None:
        expected = expected_platform()
        mapping = {
            "valid-package": "valid-0201.zip",
            "tampered-title-package": "tampered-title.zip",
            "bad-schema-package": "bad-schema.zip",
            "media-hash-mismatch-package": "media-hash-mismatch.zip",
            "missing-media-package": "missing-media.zip",
        }
        for directory, zip_name in mapping.items():
            with self.subTest(package=directory):
                verdict = evaluate(read_package_dir(directory))
                self.assertEqual(verdict.ok, expected[zip_name]["target_status"] == 201, verdict.message)
                if not verdict.ok:
                    self.assertEqual(verdict.code, expected[zip_name]["code"])

    def test_structure_invalid_is_rejected(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        del plan["knowledgeGoals"]
        files = build_package(plan, report=plugin_report(plan))
        verdict = evaluate(files)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.code, "STRUCTURE_INVALID")
        self.assertTrue(verdict.details.get("issues"))

    def test_stale_report_is_inconsistent(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        old_report = load_json_bytes(read_package_dir("valid-package")["plan.review.json"])
        plan["activityFlow"]["summary"] = "修改课堂小结，使旧报告失效"
        files = build_package(plan, report=old_report)
        verdict = evaluate(files)
        self.assertEqual(verdict.code, "REPORT_INCONSISTENT")

    def test_waived_without_override_is_rejected(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        report = plugin_report(plan)
        finding = {
            "id": "AR-0000000001",
            "round": 1,
            "severity": "major",
            "hypothesis": "演示反例",
            "evidence": ["证据"],
            "affectedPaths": ["activityFlow.summary"],
            "whyItBreaksTheLoop": "原因",
            "minimalRepair": "修复",
            "status": "waived",
        }
        report["findings"] = [finding]
        report["status"] = "passed_with_override"
        report["attestation"] = "no_counterexample"
        files = build_package(plan, report=report)
        verdict = evaluate(files)
        self.assertEqual(verdict.code, "REPORT_INCONSISTENT")
        self.assertIn("放行", verdict.message)

    def test_round_must_follow_previous(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        files = build_package(plan, report=plugin_report(plan))
        verdict = evaluate(files, previous_round=1)
        self.assertEqual(verdict.code, "REPORT_INCONSISTENT")
        self.assertIn("轮次", verdict.message)

    def test_hash_invariant_to_key_order_and_escape(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        reordered = {key: copy.deepcopy(plan[key]) for key in reversed(list(plan))}
        escaped = json.loads(json.dumps(plan, ensure_ascii=True))
        self.assertEqual(engine.plan_hash(plan), engine.plan_hash(reordered))
        self.assertEqual(engine.plan_hash(plan), engine.plan_hash(escaped))

    def test_undeclared_extra_file_is_rejected(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        files = build_package(plan, report=plugin_report(plan))
        files["media/extra.png"] = b"not-declared"
        verdict = evaluate(files)
        self.assertEqual(verdict.code, "PAYLOAD_REJECTED")


if __name__ == "__main__":
    unittest.main()
