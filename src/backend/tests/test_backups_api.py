# -*- coding: utf-8 -*-
"""OPS-08 管理端备份：创建、列表、下载、恢复到 staging 与审计。"""
from __future__ import annotations

import os
import shutil
import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestBackupsApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self._backup = self.root / "backups"
        os.environ["LPP_BACKUP_DIR"] = str(self._backup)
        self.connection = open_database(self.root / "app.db")
        self.repo = Repo(self.connection)
        self.admin = self.repo.insert_user("admin1", "管理员", "admin", security.hash_password(PASSWORD), "")
        self.teacher = self.repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD), "计算机")
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.connection.close()
        self._env.__exit__(None, None, None)
        for path in self.root.parent.glob("data-restore-*"):
            shutil.rmtree(path, ignore_errors=True)
        os.environ.pop("LPP_BACKUP_DIR", None)
        self._tmp.__exit__(None, None, None)

    def _login(self, username: str) -> str:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        return str(response.json()["csrfToken"])

    def test_backup_create_download_restore_and_audit(self) -> None:
        csrf = self._login("admin1")
        created = self.client.post(
            "/api/v1/admin/backups", json={"label": "manual"}, headers={"X-CSRF-Token": csrf}
        )
        self.assertEqual(created.status_code, 200, created.text)
        name = created.json()["name"]
        listed = self.client.get("/api/v1/admin/backups")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn(name, [item["name"] for item in listed.json()["items"]])
        downloaded = self.client.get(f"/api/v1/admin/backups/{name}/download")
        self.assertEqual(downloaded.status_code, 200, downloaded.text)
        self.assertEqual(downloaded.headers["content-type"], "application/zip")
        restored = self.client.post(
            f"/api/v1/admin/backups/{name}/restore",
            json={"confirm": True},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertTrue(restored.json()["target"].startswith(str(self.root.parent / "data-restore")))
        actions = [row[0] for row in self.connection.execute("SELECT action FROM audit_log")]
        self.assertIn("backup.create", actions)
        self.assertIn("backup.restore", actions)

    def test_teacher_is_forbidden(self) -> None:
        self._login("teacher1")
        self.assertEqual(self.client.get("/api/v1/admin/backups").status_code, 403)

    def test_bad_label_is_rejected_and_writes_nothing(self) -> None:
        csrf = self._login("admin1")
        for label in ("../../evil", "a/b", "中文标签", "a b", "x" * 41, "..", "v1.", "..."):
            with self.subTest(label=label):
                response = self.client.post(
                    "/api/v1/admin/backups", json={"label": label}, headers={"X-CSRF-Token": csrf}
                )
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(response.json()["code"], "PAYLOAD_REJECTED")
        # 备份根之外不能出现任何东西；根内也不该留下半成品
        self.assertFalse((self.root.parent / "evil").exists())
        self.assertEqual(list(self._backup.glob("*")) or [], [])

    def test_label_with_dot_keeps_archive_path_in_sync(self) -> None:
        csrf = self._login("admin1")
        created = self.client.post(
            "/api/v1/admin/backups", json={"label": "v1.0"}, headers={"X-CSRF-Token": csrf}
        )
        self.assertEqual(created.status_code, 200, created.text)
        name = created.json()["name"]
        self.assertTrue(name.endswith("-v1.0"))
        listed = self.client.get("/api/v1/admin/backups").json()
        item = next(entry for entry in listed["items"] if entry["name"] == name)
        self.assertTrue(item["hasZip"])
        downloaded = self.client.get(f"/api/v1/admin/backups/{name}/download")
        self.assertEqual(downloaded.status_code, 200, downloaded.text)
        self.assertEqual(downloaded.content[:2], b"PK")


if __name__ == "__main__":
    unittest.main()
