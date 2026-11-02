# -*- coding: utf-8 -*-
"""入库 HTTP 入口：黄金契约包、幂等、权限与 CSRF。"""
from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from support import (
    isolated_data_dir,
    package_zip,
    read_package_dir,
    tempdir,
)

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestImportApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        connection = open_database(self.db_file)
        repo = Repo(connection)
        for role in ("teacher", "lead", "admin"):
            repo.insert_user(f"{role}1", f"{role}用户", role, security.hash_password(PASSWORD))
        connection.close()
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _login(self, role: str = "teacher") -> str:
        response = self.client.post(
            "/api/v1/auth/login", json={"username": f"{role}1", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["csrfToken"]

    def _upload(self, data: bytes, csrf: str, filename: str = "package.zip"):
        return self.client.post(
            "/api/v1/plans/import",
            files={"file": (filename, data, "application/zip")},
            headers={"X-CSRF-Token": csrf},
        )

    def _version_count(self) -> int:
        connection = open_database(self.db_file)
        try:
            return int(connection.execute("SELECT COUNT(*) FROM plan_version").fetchone()[0])
        finally:
            connection.close()

    def _audit_actions(self) -> list[str]:
        connection = open_database(self.db_file)
        try:
            return [str(row["action"]) for row in Repo(connection).list_audit(100)]
        finally:
            connection.close()

    def test_valid_package_returns_201_and_is_idempotent(self) -> None:
        csrf = self._login()
        data = package_zip("valid-0201.zip")
        created = self._upload(data, csrf)
        self.assertEqual(created.status_code, 201, created.text)
        body = created.json()
        self.assertEqual(body["versionNo"], 1)
        self.assertFalse(body["duplicate"])
        self.assertTrue(body["planHash"])
        again = self._upload(data, csrf)
        self.assertEqual(again.status_code, 200, again.text)
        self.assertTrue(again.json()["duplicate"])
        self.assertEqual(again.json()["planHash"], body["planHash"])
        self.assertEqual(self._version_count(), 1)
        self.assertIn("plan.import", self._audit_actions())

    def test_tampered_package_returns_hash_mismatch(self) -> None:
        csrf = self._login()
        response = self._upload(package_zip("tampered-title.zip"), csrf)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["code"], "HASH_MISMATCH")
        self.assertEqual(self._version_count(), 0)

    def test_missing_media_returns_media_missing(self) -> None:
        csrf = self._login()
        response = self._upload(package_zip("missing-media.zip"), csrf)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["code"], "MEDIA_MISSING")

    def test_zip_slip_returns_payload_rejected(self) -> None:
        csrf = self._login()
        response = self._upload(package_zip("zip-slip.zip"), csrf)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["code"], "PAYLOAD_REJECTED")

    def test_requires_session_role_and_csrf(self) -> None:
        self.assertEqual(self._upload(package_zip("valid-0201.zip"), "").status_code, 401)
        admin_csrf = self._login("admin")
        forbidden = self._upload(package_zip("valid-0201.zip"), admin_csrf)
        self.assertEqual(forbidden.status_code, 403, forbidden.text)
        teacher_csrf = self._login("teacher")
        no_csrf = self._upload(package_zip("valid-0201.zip"), "")
        self.assertEqual(no_csrf.status_code, 403)

    def test_lead_can_import(self) -> None:
        csrf = self._login("lead")
        response = self._upload(package_zip("valid-0201.zip"), csrf)
        self.assertEqual(response.status_code, 201, response.text)

    def test_oversize_package_returns_413(self) -> None:
        previous = os.environ.get("LPP_MAX_PACKAGE_BYTES")
        os.environ["LPP_MAX_PACKAGE_BYTES"] = "1024"
        try:
            csrf = self._login()
            response = self._upload(package_zip("valid-0201.zip"), csrf)
        finally:
            if previous is None:
                os.environ.pop("LPP_MAX_PACKAGE_BYTES", None)
            else:
                os.environ["LPP_MAX_PACKAGE_BYTES"] = previous
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(response.json()["code"], "PAYLOAD_TOO_LARGE")

    def test_files_are_stored_under_data_dir(self) -> None:
        csrf = self._login()
        body = self._upload(package_zip("valid-0201.zip"), csrf).json()
        stored = self.root / "files" / "plans" / str(body["planId"]) / str(body["versionNo"]) / "plan.json"
        self.assertTrue(stored.is_file())


if __name__ == "__main__":
    unittest.main()
