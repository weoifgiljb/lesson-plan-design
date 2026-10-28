# -*- coding: utf-8 -*-
"""证据链五项判定（纯函数）。"""
from __future__ import annotations

import unittest

from app.domain import evidence


def report(**overrides) -> dict:
    base = {
        "planHash": "hash-1",
        "round": 1,
        "reviewer": "native_subagent",
        "independence": "native_subagent",
        "structuralValidation": {"ok": True},
        "findings": [],
        "overrides": [],
        "status": "passed",
        "attestation": "no_counterexample",
        "planSnapshot": {"same": "plan"},
    }
    base.update(overrides)
    return base


def snapshot_hash(value: dict | None) -> str | None:
    return "hash-1" if isinstance(value, dict) else None


def chain(data: dict, *, rounds: list[int] | None = None, plan_hash: str = "hash-1") -> dict:
    return evidence.evaluate(
        data,
        plan_hash=plan_hash,
        rounds=rounds if rounds is not None else [1],
        snapshot_hash=snapshot_hash(data.get("planSnapshot")),
    )


class TestEvidenceChain(unittest.TestCase):
    def test_clean_report_is_complete(self) -> None:
        result = chain(report())
        self.assertTrue(result["complete"], result)
        self.assertEqual((result["passed"], result["total"]), (5, 5))
        self.assertEqual(result["gaps"], [])
        self.assertEqual(len(result["items"]), 5)

    def test_hash_mismatch_is_flagged(self) -> None:
        result = chain(report(planHash="other"))
        self.assertIn("hash_match", result["gaps"])
        self.assertEqual(result["passed"], 4)

    def test_round_gap_is_flagged(self) -> None:
        result = chain(report(round=3), rounds=[1, 3])
        self.assertIn("round_continuous", result["gaps"])

    def test_duplicate_round_is_flagged(self) -> None:
        result = chain(report(round=2), rounds=[1, 2, 2])
        self.assertIn("round_continuous", result["gaps"])

    def test_waived_without_override_is_flagged(self) -> None:
        finding = {"id": "AR-1", "severity": "major", "status": "waived"}
        result = chain(report(findings=[finding], status="passed_with_override"))
        self.assertIn("overrides_complete", result["gaps"])

    def test_orphan_override_is_flagged(self) -> None:
        override = {
            "findingId": "AR-404",
            "planHash": "hash-1",
            "teacher": "张老师",
            "reason": "已与教研组确认",
            "kind": "teacher_override",
        }
        result = chain(report(overrides=[override]))
        self.assertIn("overrides_complete", result["gaps"])

    def test_bad_independence_is_flagged(self) -> None:
        result = chain(report(independence="robot", reviewer="robot"))
        self.assertIn("independence_valid", result["gaps"])

    def test_status_contradiction_is_flagged(self) -> None:
        open_finding = {"id": "AR-1", "severity": "major", "status": "open"}
        result = chain(report(findings=[open_finding], status="passed", attestation="no_counterexample"))
        self.assertIn("status_consistent", result["gaps"])

    def test_pending_reviewer_with_findings_is_flagged(self) -> None:
        finding = {"id": "AR-1", "severity": "major", "status": "open"}
        result = chain(report(findings=[finding], status="pending_reviewer", attestation=None))
        self.assertIn("status_consistent", result["gaps"])

    def test_six_states_are_recognised(self) -> None:
        waived = {"id": "AR-1", "severity": "major", "status": "waived"}
        accepted = {"id": "AR-2", "severity": "minor", "status": "accepted"}
        cases = [
            (report(), [1]),
            (
                report(
                    findings=[waived],
                    overrides=[
                        {"findingId": "AR-1", "planHash": "hash-1", "teacher": "张老师", "reason": "已与教研组确认", "kind": "teacher_override"}
                    ],
                    status="passed_with_override",
                ),
                [1],
            ),
            (
                report(
                    findings=[accepted],
                    overrides=[
                        {"findingId": "AR-2", "planHash": "hash-1", "teacher": "张老师", "reason": "下次修订一并处理", "kind": "minor_acceptance"}
                    ],
                    status="passed_with_accepted_minor",
                ),
                [1],
            ),
            (report(findings=[{"id": "AR-3", "severity": "blocker", "status": "open"}], status="needs_repair"), [1]),
            (report(status="pending_reviewer", attestation=None), [1]),
            (report(structuralValidation={"ok": False}, status="structure_invalid"), [1]),
        ]
        for data, rounds in cases:
            with self.subTest(status=data["status"]):
                self.assertTrue(chain(data, rounds=rounds)["complete"])


if __name__ == "__main__":
    unittest.main()
