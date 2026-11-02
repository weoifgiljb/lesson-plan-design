# -*- coding: utf-8 -*-
"""统计口径黄金数据：20 份构造数据，逐项断言分子/分母/值。"""
from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, load_json_bytes, read_package_dir, tempdir

from app.adapters import engine
from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security

PASSWORD = "Lesson2026"
TOTAL = 20
VALID = 19          # 19 份结构合规
OPEN_MAJOR = 2      # 2 份带未关闭 major
EVIDENCE_OK = 10    # 10 份证据链完整


class TestStatsGolden(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        self.plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        self._seed()
        from app.main import create_app

        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _seed(self) -> None:
        connection = open_database(self.db_file)
        repo = Repo(connection)
        repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD), "计算机")
        for index in range(TOTAL):
            valid = index != 0
            plan = json.loads(json.dumps(self.plan))
            if not valid:
                plan.pop("week", None)
            content = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            plan_hash = engine.plan_hash(plan)
            cursor = connection.execute(
                "INSERT INTO plan (owner_id, content_title, week, session, course, created_at)"
                " VALUES (1, ?, ?, ?, '信息技术', ?)",
                (f"课题{index}", 2 + index, 1, "2026-10-30T00:00:00+00:00"),
            )
            plan_id = int(cursor.lastrowid)
            status = "needs_repair" if index < OPEN_MAJOR else "passed"
            version = connection.execute(
                "INSERT INTO plan_version (plan_id, version_no, content_json, plan_hash, schema_version,"
                " rubric_version, created_at) VALUES (?, 1, ?, ?, 1, '1.0', ?)",
                (plan_id, content, plan_hash, "2026-10-30T00:00:00+00:00"),
            )
            version_id = int(version.lastrowid)
            connection.execute(
                "UPDATE plan SET current_version_id = ? WHERE id = ?", (version_id, plan_id)
            )
            findings = []
            evidence_ok = index >= TOTAL - EVIDENCE_OK
            if index < OPEN_MAJOR:
                findings.append({"id": "AR-1", "severity": "major", "status": "open"})
            elif not evidence_ok:
                # 状态与问题闭环不一致 → 证据链不完整（但不计入 defect_density）
                findings.append({"id": "AR-2", "severity": "minor", "status": "open"})
            report = {
                "planHash": plan_hash if evidence_ok else "wrong-hash",
                "round": 1,
                "reviewer": "native_subagent",
                "independence": "native_subagent",
                "structuralValidation": {"ok": valid},
                "findings": findings,
                "overrides": [],
                "status": status,
                "attestation": "no_counterexample",
            }
            if evidence_ok:
                report["planSnapshot"] = plan
            connection.execute(
                "INSERT INTO review (plan_version_id, round, report_json, report_sha256, status,"
                " reviewer_mode, created_at) VALUES (?, 1, ?, ?, ?, 'native_subagent', ?)",
                (
                    version_id,
                    json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    f"report-{index}",
                    status,
                    "2026-10-30T00:00:00+00:00",
                ),
            )
        connection.commit()
        connection.close()

    def _metrics(self) -> dict:
        connection = open_database(self.db_file)
        try:
            repo = Repo(connection)
            user = repo.user_by_username("teacher1")
        finally:
            connection.close()
        response = self.client.post(
            "/api/v1/auth/login", json={"username": "teacher1", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = self.client.get("/api/v1/stats/summary").json()
        return {item["key"]: item for item in body["metrics"]}

    def test_golden_ratios(self) -> None:
        metrics = self._metrics()
        structure = metrics["structure_rate"]
        self.assertEqual(structure["denominator"], TOTAL)
        self.assertEqual(structure["numerator"], VALID)
        self.assertAlmostEqual(structure["value"], VALID / TOTAL, places=4)

        defect = metrics["defect_density"]
        self.assertEqual(defect["denominator"], TOTAL)
        self.assertEqual(defect["numerator"], OPEN_MAJOR)

        evidence = metrics["evidence_rate"]
        self.assertEqual(evidence["denominator"], TOTAL)
        self.assertEqual(evidence["numerator"], EVIDENCE_OK)
        self.assertAlmostEqual(evidence["value"], EVIDENCE_OK / TOTAL, places=4)

    def test_drilldown_matches_denominator(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login", json={"username": "teacher1", "password": PASSWORD}
        )
        self.assertEqual(login.status_code, 200, login.text)
        response = self.client.get("/api/v1/stats/records?pageSize=50")
        self.assertEqual(response.status_code, 200, response.text)
        listing = response.json()
        self.assertEqual(listing["total"], TOTAL)
        self.assertEqual(len(listing["items"]), TOTAL)
        first = listing["items"][0]
        for key in ("planId", "reviewId", "course", "week", "session", "structureOk", "evidenceOk", "openBlocking"):
            self.assertIn(key, first)
        # 结构不合规的那份必须出现在下钻里且 structureOk=false
        invalid = [item for item in listing["items"] if not item["structureOk"]]
        self.assertEqual(len(invalid), TOTAL - VALID)
        # 分页
        page2 = self.client.get("/api/v1/stats/records?page=2&pageSize=10").json()
        self.assertEqual(page2["page"], 2)
        self.assertEqual(len(page2["items"]), 10)
        self.assertEqual(page2["total"], TOTAL)


if __name__ == "__main__":
    unittest.main()
