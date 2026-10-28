# -*- coding: utf-8 -*-
"""双端同步 API：头版本、游标拉取、baseHash 推送与 409 冲突。"""
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


class TestSyncApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        connection = open_database(self.db_file)
        repo = Repo(connection)
        for role, group in (("teacher", "计算机"), ("lead", "计算机"), ("admin", "")):
            repo.insert_user(f"{role}1", f"{role}用户", role, security.hash_password(PASSWORD), group)
        repo.insert_user("teacher2", "李老师", "teacher", security.hash_password(PASSWORD), "英语")
        connection.close()
        self.client = TestClient(create_app())
        self.client.__enter__()
        self.csrf = self._login("teacher1")
        first = self._import()
        self.plan_id = first["planId"]
        self.first_hash = first["planHash"]

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

    def _package(self, round_number: int, summary: str, previous: dict | None) -> dict[str, bytes]:
        files = read_package_dir("valid-package")
        plan = load_json_bytes(files["plan.json"])
        plan["activityFlow"]["summary"] = summary
        report = plugin_report(plan, round_number=round_number, previous_report=previous)
        return build_package(plan, report=report)

    def _push(self, files: dict[str, bytes], base_hash: str, csrf: str | None = None):
        import zipfile
        from io import BytesIO

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as handle:
            for name, data in files.items():
                handle.writestr(name, data)
        return self.client.post(
            "/api/v1/sync/push",
            files={"file": ("pkg.zip", buffer.getvalue(), "application/zip")},
            data={"baseHash": base_hash},
            headers={"X-CSRF-Token": csrf or self.csrf},
        )

    def _sync_log(self) -> list[dict]:
        connection = open_database(self.db_file)
        try:
            return [dict(row) for row in connection.execute("SELECT * FROM sync_log ORDER BY id").fetchall()]
        finally:
            connection.close()

    def test_head_by_id_and_identity(self) -> None:
        by_id = self.client.get(f"/api/v1/sync/head?planId={self.plan_id}").json()
        self.assertTrue(by_id["exists"])
        self.assertEqual(by_id["headVersion"], 1)
        self.assertEqual(by_id["headHash"], self.first_hash)
        by_identity = self.client.get(
            "/api/v1/sync/head?course=信息技术&week=2&session=1&contentTitle=一级考证辅导2"
        ).json()
        self.assertEqual(by_identity["planId"], self.plan_id)
        self.assertEqual(self.client.get("/api/v1/sync/head?planId=9999").status_code, 404)
        self._login("teacher2")
        self.assertEqual(self.client.get(f"/api/v1/sync/head?planId={self.plan_id}").status_code, 403)

    def test_pull_cursor_and_scope(self) -> None:
        listing = self.client.get("/api/v1/sync/pull?since=0").json()
        self.assertEqual(len(listing["items"]), 1)
        self.assertEqual(listing["items"][0]["planId"], self.plan_id)
        self.assertEqual(listing["items"][0]["contentTitle"], "一级考证辅导2")
        self.assertIn("activityFlow", listing["items"][0]["content"])
        cursor = listing["nextCursor"]
        after = self.client.get(f"/api/v1/sync/pull?since={cursor}").json()
        self.assertEqual(after["items"], [])
        self.assertEqual(after["nextCursor"], cursor)
        self._login("teacher2")
        self.assertEqual(self.client.get("/api/v1/sync/pull?since=0").json()["items"], [])

    def test_push_duplicate_is_idempotent(self) -> None:
        response = self._push(read_package_dir("valid-package"), self.first_hash)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["duplicate"])
        logs = [row["result"] for row in self._sync_log()]
        self.assertIn("duplicate", logs)

    def test_push_new_version_updates_head(self) -> None:
        previous = load_json_bytes(read_package_dir("valid-package")["plan.review.json"])
        package = self._package(2, "第二次同步修订", previous)
        response = self._push(package, self.first_hash)
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["versionNo"], 2)
        self.assertEqual(body["headVersion"], 2)
        head = self.client.get(f"/api/v1/sync/head?planId={self.plan_id}").json()
        self.assertEqual(head["headVersion"], 2)
        self.assertNotEqual(head["headHash"], self.first_hash)
        self.assertEqual(len(self.client.get("/api/v1/sync/pull?since=0").json()["items"]), 2)

    def test_stale_base_hash_returns_409(self) -> None:
        previous = load_json_bytes(read_package_dir("valid-package")["plan.review.json"])
        second = self._package(2, "第二次同步修订", previous)
        self.assertEqual(self._push(second, self.first_hash).status_code, 201)
        old_hash = self.first_hash
        second_report = load_json_bytes(second["plan.review.json"])
        third = self._package(3, "第三次同步修订", second_report)
        response = self._push(third, old_hash)
        self.assertEqual(response.status_code, 409, response.text)
        body = response.json()
        self.assertEqual(body["code"], "CONFLICT_STALE")
        self.assertEqual(body["details"]["headVersion"], 2)
        self.assertEqual(body["details"]["baseHash"], old_hash)
        self.assertTrue(body["details"]["changes"])
        logs = [row for row in self._sync_log() if row["result"] == "conflict"]
        self.assertEqual(len(logs), 1)
        connection = open_database(self.db_file)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM plan_version").fetchone()[0], 2)
        finally:
            connection.close()

    def test_duplicate_retry_without_base_hash_is_idempotent(self) -> None:
        response = self._push(read_package_dir("valid-package"), "")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["duplicate"])

    def test_missing_base_hash_conflicts_for_new_content(self) -> None:
        previous = load_json_bytes(read_package_dir("valid-package")["plan.review.json"])
        package = self._package(2, "未带 baseHash 的新内容", previous)
        response = self._push(package, "")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "CONFLICT_STALE")

    def test_new_plan_without_base_hash(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        plan["contentTitle"] = "同步新课"
        package = build_package(plan, report=plugin_report(plan))
        response = self._push(package, "")
        self.assertEqual(response.status_code, 201, response.text)
        self.assertNotEqual(response.json()["planId"], self.plan_id)

    def test_lead_can_push_own_plan(self) -> None:
        csrf = self._login("lead1")
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        plan["contentTitle"] = "组长同步课"
        package = build_package(plan, report=plugin_report(plan))
        response = self._push(package, "", csrf)
        self.assertEqual(response.status_code, 201, response.text)

    def test_admin_cannot_use_sync(self) -> None:
        csrf = self._login("admin1")
        self.assertEqual(self.client.get("/api/v1/sync/pull").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/sync/head?planId=1").status_code, 403)
        response = self._push(read_package_dir("valid-package"), "", csrf)
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
