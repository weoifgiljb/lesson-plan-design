# -*- coding: utf-8 -*-
"""BS-16 运维指标：管理员可见、失败率/冲突率计算。"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestMetricsApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.connection = open_database(self.root / "app.db")
        self.repo = Repo(self.connection)
        self.admin = self.repo.insert_user("admin1", "管理员", "admin", security.hash_password(PASSWORD), "")
        self.teacher = self.repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD), "计算机")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        plan_id = self.connection.execute(
            "INSERT INTO plan (owner_id, content_title, week, session, course, created_at)"
            " VALUES (?, '指标课', 1, 1, '信息技术', ?)",
            (self.teacher, now),
        ).lastrowid
        version_id = self.connection.execute(
            "INSERT INTO plan_version (plan_id, version_no, content_json, plan_hash, engine_version, schema_version, rubric_version, created_at)"
            " VALUES (?, 1, '{}', 'hash', '1.0.0', 13, '1.1.0', ?)",
            (plan_id, now),
        ).lastrowid
        for status in ("succeeded", "failed"):
            self.connection.execute(
                "INSERT INTO export_job (plan_version_id, engine_version, status, operator_id, created_at)"
                " VALUES (?, '1.0.0', ?, ?, ?)",
                (version_id, status, self.teacher, now),
            )
        self.repo.insert_sync_log("push", "pkg", "hash", "created", "", self.teacher)
        self.repo.insert_sync_log("push", "pkg2", "hash2", "rejected", "CONFLICT_STALE", self.teacher)
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.connection.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _login(self, username: str) -> None:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)

    def test_admin_sees_rates(self) -> None:
        self._login("admin1")
        response = self.client.get("/api/v1/metrics/ops")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["export"]["total"], 2)
        self.assertEqual(body["export"]["failed"], 1)
        self.assertEqual(body["export"]["failureRate"], 0.5)
        self.assertEqual(body["sync"]["conflicts"], 1)
        self.assertEqual(body["sync"]["conflictRate"], 0.5)
        self.assertEqual(body["logRetentionDays"], 30)
        self.assertEqual({item["code"] for item in body["alerts"]}, {"EXPORT_FAILURE_RATE", "SYNC_CONFLICT_RATE"})

    def test_teacher_is_forbidden(self) -> None:
        self._login("teacher1")
        self.assertEqual(self.client.get("/api/v1/metrics/ops").status_code, 403)


if __name__ == "__main__":
    unittest.main()
