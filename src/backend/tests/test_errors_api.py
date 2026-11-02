# -*- coding: utf-8 -*-
"""错误信封、415 与畸形包走 HTTP 的端到端行为。"""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from factories import build_package
from support import isolated_data_dir, load_json_bytes, package_zip, plugin_report, read_package_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestErrorEnvelope(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        connection = open_database(self.root / "app.db")
        repo = Repo(connection)
        repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD))
        connection.close()
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _login(self) -> str:
        response = self.client.post(
            "/api/v1/auth/login", json={"username": "teacher1", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["csrfToken"]

    def test_unknown_route_uses_error_envelope(self) -> None:
        response = self.client.get("/api/v1/does-not-exist")
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body["code"], "NOT_FOUND")
        self.assertTrue(body["traceId"])

    def test_wrong_content_type_returns_415(self) -> None:
        csrf = self._login()
        response = self.client.post(
            "/api/v1/plans/import",
            files={"file": ("pkg.txt", b"not-a-zip", "text/plain")},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(response.status_code, 415, response.text)
        self.assertEqual(response.json()["code"], "UNSUPPORTED_MEDIA")

    def test_malformed_plan_returns_422_and_writes_rejection_audit(self) -> None:
        csrf = self._login()
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        plan["session"] = {"bad": 1}
        files = build_package(plan, report=plugin_report(plan))
        import zipfile
        from io import BytesIO

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as handle:
            for name, data in files.items():
                handle.writestr(name, data)
        response = self.client.post(
            "/api/v1/plans/import",
            files={"file": ("bad.zip", buffer.getvalue(), "application/zip")},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["code"], "STRUCTURE_INVALID")
        connection = open_database(self.root / "app.db")
        try:
            actions = [row["action"] for row in Repo(connection).list_audit(50)]
        finally:
            connection.close()
        self.assertIn("plan.import.rejected", actions)

    def test_valid_package_after_regressions(self) -> None:
        csrf = self._login()
        response = self.client.post(
            "/api/v1/plans/import",
            files={"file": ("ok.zip", package_zip("valid-0201.zip"), "application/zip")},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(response.status_code, 201, response.text)


if __name__ == "__main__":
    unittest.main()
