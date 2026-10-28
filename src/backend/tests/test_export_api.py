# -*- coding: utf-8 -*-
"""导出中心 API：门禁、批量导出、复用、权限与下载。"""
from __future__ import annotations

import hashlib
import unittest
import zipfile

from fastapi.testclient import TestClient

from support import isolated_data_dir, package_zip, tempdir

from app.adapters import storage
from app.adapters.db.connection import open_database
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestExportApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        connection = open_database(self.db_file)
        for username, role, group in (
            ("teacher1", "teacher", "计算机"),
            ("teacher2", "teacher", "英语"),
            ("lead1", "lead", "计算机"),
            ("admin1", "admin", ""),
        ):
            connection.execute(
                "INSERT INTO user (username, display_name, group_name, role, password_hash, created_at)"
                " VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (username, username, group, role, security.hash_password(PASSWORD)),
            )
        connection.commit()
        connection.close()
        self.client = TestClient(create_app())
        self.client.__enter__()
        self.csrf = self._login("teacher1")
        imported = self._import()
        self.plan_id = imported["planId"]
        self.version_id = self._version_id()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _login(self, username: str) -> str:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["csrfToken"]

    def _import(self) -> dict:
        response = self.client.post(
            "/api/v1/plans/import",
            files={"file": ("valid.zip", package_zip("valid-0201.zip"), "application/zip")},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def _version_id(self) -> int:
        connection = open_database(self.db_file)
        try:
            return int(
                connection.execute(
                    "SELECT id FROM plan_version WHERE plan_id = ? ORDER BY version_no DESC LIMIT 1",
                    (self.plan_id,),
                ).fetchone()[0]
            )
        finally:
            connection.close()

    def _export(self, ids: list[int], csrf: str | None = None):
        return self.client.post(
            "/api/v1/exports",
            json={"planVersionIds": ids},
            headers={"X-CSRF-Token": csrf or self.csrf},
        )

    def test_export_success_and_reuse(self) -> None:
        response = self._export([self.version_id])
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()["items"][0]
        self.assertEqual(item["status"], "succeeded")
        self.assertEqual(item["planVersionId"], self.version_id)
        path = storage.export_path(int(item["exportId"]))
        self.assertTrue(path.exists())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(item["docxSha256"], digest)
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
        self.assertIn("word/document.xml", names)
        self.assertIn("word/footer1.xml", names)
        again = self._export([self.version_id])
        self.assertEqual(again.status_code, 200, again.text)
        self.assertTrue(again.json()["reused"])
        self.assertEqual(again.json()["items"][0]["exportId"], item["exportId"])

    def test_detail_and_download(self) -> None:
        item = self._export([self.version_id]).json()["items"][0]
        detail = self.client.get(f"/api/v1/exports/{item['exportId']}")
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["status"], "succeeded")
        download = self.client.get(f"/api/v1/exports/{item['exportId']}/download")
        self.assertEqual(download.status_code, 200, download.text)
        self.assertTrue(download.content.startswith(b"PK"))
        self.assertEqual(download.headers["X-Docx-Sha256"], item["docxSha256"])
        self.assertIn("attachment", download.headers["Content-Disposition"])

    def test_gate_failure_blocks_export(self) -> None:
        connection = open_database(self.db_file)
        try:
            connection.execute(
                "UPDATE review SET status = 'needs_repair' WHERE plan_version_id = ?",
                (self.version_id,),
            )
        finally:
            connection.close()
        response = self._export([self.version_id])
        self.assertEqual(response.status_code, 201)
        item = response.json()["items"][0]
        self.assertEqual(item["status"], "failed")
        self.assertEqual(item["code"], "REPORT_INCONSISTENT")

    def test_teacher_cannot_export_others(self) -> None:
        csrf = self._login("teacher2")
        response = self._export([self.version_id], csrf)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["items"][0]["code"], "FORBIDDEN")

    def test_invalid_payload(self) -> None:
        self.assertEqual(self._export([]).status_code, 422)
        self.assertEqual(self._export(list(range(1, 52))).status_code, 422)
        self.assertEqual(self._export([0]).status_code, 422)

    def test_admin_cannot_use_export(self) -> None:
        csrf = self._login("admin1")
        response = self._export([self.version_id], csrf)
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
