# -*- coding: utf-8 -*-
"""样例库 API：上传校验、重复、列表筛选与完整性。"""
from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, load_json_bytes, read_package_dir, tempdir

from app.adapters import storage
from app.adapters.db.connection import open_database
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestSamplesApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        connection = open_database(self.db_file)
        for username, role in (("admin1", "admin"), ("teacher1", "teacher"), ("lead1", "lead")):
            connection.execute(
                "INSERT INTO user (username, display_name, group_name, role, password_hash, created_at)"
                " VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (username, username, "计算机", role, security.hash_password(PASSWORD)),
            )
        connection.close()
        self.plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _login(self, username: str) -> str:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["csrfToken"]

    def _upload(self, plan: dict, csrf: str, content_type: str = "application/json"):
        return self.client.post(
            "/api/v1/samples",
            files={"file": ("plan.json", json.dumps(plan, ensure_ascii=False).encode("utf-8"), content_type)},
            headers={"X-CSRF-Token": csrf},
        )

    def test_admin_uploads_sample(self) -> None:
        csrf = self._login("admin1")
        response = self._upload(self.plan, csrf)
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["title"], self.plan["contentTitle"])
        self.assertTrue(body["complete"])
        connection = open_database(self.db_file)
        try:
            row = connection.execute("SELECT * FROM sample").fetchone()
            audit = connection.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'sample.create'").fetchone()[0]
        finally:
            connection.close()
        self.assertIsNotNone(row)
        self.assertEqual(audit, 1)

    def test_duplicate_sample_conflicts(self) -> None:
        csrf = self._login("admin1")
        self.assertEqual(self._upload(self.plan, csrf).status_code, 201)
        self.assertEqual(self._upload(self.plan, csrf).status_code, 409)

    def test_invalid_structure_is_rejected_with_issues(self) -> None:
        plan = json.loads(json.dumps(self.plan))
        plan["week"] = ["第二周"]
        response = self._upload(plan, self._login("admin1"))
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["code"], "STRUCTURE_INVALID")
        self.assertTrue(response.json()["details"]["issues"])

    def test_non_json_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/samples",
            files={"file": ("plan.json", b"not-json", "application/json")},
            headers={"X-CSRF-Token": self._login("admin1")},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["code"], "PAYLOAD_REJECTED")

    def test_teacher_and_lead_cannot_upload(self) -> None:
        for username in ("teacher1", "lead1"):
            with self.subTest(username=username):
                csrf = self._login(username)
                self.assertEqual(self._upload(self.plan, csrf).status_code, 403)

    def test_list_filters_and_incomplete(self) -> None:
        self._upload(self.plan, self._login("admin1"))
        self._login("teacher1")
        listing = self.client.get("/api/v1/samples").json()
        self.assertEqual(listing["total"], 1)
        self.assertTrue(listing["items"][0]["complete"])
        self.assertEqual(self.client.get("/api/v1/samples?course=信息技术").json()["total"], 1)
        self.assertEqual(self.client.get("/api/v1/samples?course=英语").json()["total"], 0)
        self.assertEqual(self.client.get("/api/v1/samples?q=一级考证").json()["total"], 1)
        self.assertEqual(self.client.get("/api/v1/samples?week=9").json()["total"], 0)
        connection = open_database(self.db_file)
        try:
            path = connection.execute("SELECT json_path FROM sample").fetchone()[0]
        finally:
            connection.close()
        (storage.files_dir() / path).write_bytes(b"{}")
        tampered = self.client.get("/api/v1/samples").json()
        self.assertFalse(tampered["items"][0]["complete"])


if __name__ == "__main__":
    unittest.main()
