# -*- coding: utf-8 -*-
"""统计摘要 API：教师本人、组长本组、管理员全量。"""
from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestStatsApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        connection = open_database(self.db_file)
        self.repo = Repo(connection)
        self.teacher1 = self.repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD), "计算机")
        self.teacher2 = self.repo.insert_user("teacher2", "李老师", "teacher", security.hash_password(PASSWORD), "英语")
        self.lead1 = self.repo.insert_user("lead1", "王组长", "lead", security.hash_password(PASSWORD), "计算机")
        self.admin = self.repo.insert_user("admin1", "管理员", "admin", security.hash_password(PASSWORD), "")
        self._seed()
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.repo.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _plan(self, owner: int, title: str) -> tuple[int, int]:
        plan_id = self.repo.create_plan(owner, {"contentTitle": title, "week": 2, "session": 1, "course": "信息技术"})
        version_id, _ = self.repo.insert_version_or_existing(
            plan_id, 1, "{}", f"hash-{title}", 1, "1.0", "1.0.0"
        )
        return plan_id, version_id

    def _review(self, version_id: int, status: str, findings: list | None = None) -> None:
        report = json.dumps({"status": status, "findings": findings or []}, ensure_ascii=False)
        review_id = self.repo.insert_review(version_id, 1, report, "sha-" + status, status, "native_subagent")
        if findings:
            self.repo.insert_findings(review_id, findings)

    def _seed(self) -> None:
        _, version_a = self._plan(self.teacher1, "通过课")
        self._review(version_a, "passed")
        job_id = self.repo.create_export_job(version_a, "1.0.0", self.teacher1, "pending")
        self.repo.update_export_job(job_id, "succeeded", f"exports/{job_id}.docx", "docx-sha")
        _, version_b = self._plan(self.teacher2, "退回课")
        self._review(
            version_b,
            "needs_repair",
            [{"id": "AR-1", "severity": "blocker", "status": "open"}],
        )

    def _login(self, username: str) -> None:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)

    def test_teacher_sees_own(self) -> None:
        self._login("teacher1")
        body = self.client.get("/api/v1/stats/summary").json()
        self.assertEqual(body["scope"], "own")
        self.assertEqual(body["totals"]["plans"], 1)
        self.assertEqual(body["totals"]["reviews"], 1)
        self.assertEqual(body["passRate"], 1.0)
        self.assertEqual(body["exportStatus"], {"succeeded": 1})

    def test_lead_sees_group(self) -> None:
        self._login("lead1")
        body = self.client.get("/api/v1/stats/summary").json()
        self.assertEqual(body["scope"], "group")
        self.assertEqual(body["totals"]["plans"], 1)
        self.assertEqual(body["passRate"], 1.0)

    def test_admin_sees_all(self) -> None:
        self._login("admin1")
        body = self.client.get("/api/v1/stats/summary").json()
        self.assertEqual(body["scope"], "all")
        self.assertEqual(body["totals"]["plans"], 2)
        self.assertEqual(body["totals"]["reviews"], 2)
        self.assertEqual(body["passRate"], 0.5)
        self.assertEqual(body["findingSeverity"], {"blocker": 1})
        self.assertEqual(body["findingStatus"], {"open": 1})
        self.assertEqual(body["rounds"], {"1": 2})

    def test_teacher_with_no_plans(self) -> None:
        self.repo.insert_user("teacher3", "新老师", "teacher", security.hash_password(PASSWORD), "计算机")
        self._login("teacher3")
        body = self.client.get("/api/v1/stats/summary").json()
        self.assertEqual(body["totals"]["plans"], 0)
        self.assertEqual(body["passRate"], 0.0)


if __name__ == "__main__":
    unittest.main()
