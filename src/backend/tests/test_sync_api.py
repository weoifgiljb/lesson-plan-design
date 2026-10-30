# -*- coding: utf-8 -*-
"""双端同步 API：头版本、游标拉取、baseHash 推送与 409 冲突。"""
from __future__ import annotations

import io
import json
import threading
import unittest
import zipfile

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

    def _zip(self, files: dict[str, bytes]) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as handle:
            for name, data in files.items():
                handle.writestr(name, data)
        return buffer.getvalue()

    def _push(self, files: dict[str, bytes], base_hash: str, csrf: str | None = None):
        return self.client.post(
            "/api/v1/sync/push",
            files={"file": ("pkg.zip", self._zip(files), "application/zip")},
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

    def test_old_round_package_gets_409_not_422(self) -> None:
        # TC-08-01 真实场景：平台已到 v2，客户端仍停在 v1（round 1 的包）
        previous = load_json_bytes(read_package_dir("valid-package")["plan.review.json"])
        second = self._package(2, "第二次同步修订", previous)
        self.assertEqual(self._push(second, self.first_hash).status_code, 201)
        stale = self._push(self._package(1, "旧客户端仍在 v1", None), self.first_hash)
        self.assertEqual(stale.status_code, 409, stale.text)
        details = stale.json()["details"]
        self.assertEqual(details["headVersion"], 2)
        self.assertEqual(details["baseHash"], self.first_hash)
        self.assertIn("changes", details)

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


    def test_push_malformed_structure_is_422(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        plan["week"] = ["第二周"]
        package = build_package(plan, report=plugin_report(plan))
        response = self._push(package, self.first_hash)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["code"], "STRUCTURE_INVALID")
        connection = open_database(self.db_file)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM plan_version").fetchone()[0], 1)
        finally:
            connection.close()
        rejected = [row for row in self._sync_log() if row["result"] == "rejected"]
        self.assertTrue(rejected)

    def test_tampered_manifest_is_not_duplicate(self) -> None:
        files = read_package_dir("valid-package")
        manifest = load_json_bytes(files["manifest.json"])
        manifest["reportHash"] = "0" * 64
        files["manifest.json"] = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
        response = self._push(files, self.first_hash)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn(response.json()["code"], {"HASH_MISMATCH", "REPORT_INCONSISTENT"})
        rejected = [row for row in self._sync_log() if row["result"] == "rejected"]
        self.assertTrue(rejected)

    def test_conflict_without_base_hash_still_has_changes(self) -> None:
        previous = load_json_bytes(read_package_dir("valid-package")["plan.review.json"])
        response = self._push(self._package(2, "缺 baseHash 但要有差异", previous), "")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertTrue(response.json()["details"]["changes"])

    def test_route_level_rejection_is_logged(self) -> None:
        response = self.client.post(
            "/api/v1/sync/push",
            files={"file": ("bad.zip", b"not-a-zip", "application/zip")},
            data={"baseHash": ""},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 422, response.text)
        rejected = [row for row in self._sync_log() if row["result"] == "rejected"]
        self.assertTrue(rejected)
        self.assertEqual(rejected[-1]["conflict_code"], "PAYLOAD_REJECTED")

    def test_pull_reports_deleted_tombstone(self) -> None:
        csrf = self.client.cookies.get("lpp_csrf")
        deleted = self.client.delete(f"/api/v1/plans/{self.plan_id}", headers={"X-CSRF-Token": csrf})
        self.assertEqual(deleted.status_code, 200, deleted.text)
        items = self.client.get("/api/v1/sync/pull?since=0").json()["items"]
        self.assertTrue(items)
        # 只有 kind=deleted 才是墓碑；历史 version 事件不能被标成 deleted（R3-F1）
        tombstones = [item for item in items if item["kind"] == "deleted"]
        self.assertEqual(len(tombstones), 1, items)
        self.assertEqual(tombstones[0]["planId"], self.plan_id)
        self.assertNotIn("content", tombstones[0])
        versions = [item for item in items if item["kind"] == "version"]
        self.assertTrue(versions, items)
        self.assertTrue(all(item["deleted"] is False for item in versions), versions)
        # 教案已删可通过 planDeleted 表达
        self.assertTrue(all(item["planDeleted"] for item in items), items)

    def test_delete_propagates_after_cursor(self) -> None:
        # 先把游标推到最新，再删除；下一次 pull 必须能拉到 deleted 事件（P24 R1 的核心场景）
        first = self.client.get("/api/v1/sync/pull?since=0").json()
        cursor = first["nextCursor"]
        self.assertGreater(cursor, 0)
        csrf = self.client.cookies.get("lpp_csrf")
        self.assertEqual(
            self.client.delete(f"/api/v1/plans/{self.plan_id}", headers={"X-CSRF-Token": csrf}).status_code,
            200,
        )
        after = self.client.get(f"/api/v1/sync/pull?since={cursor}").json()
        self.assertTrue(after["items"], after)
        kinds = [(item["kind"], item["planId"]) for item in after["items"]]
        self.assertIn(("deleted", self.plan_id), kinds)
        # head 对已删教案必须告诉客户端"不存在/已删除"
        head = self.client.get(f"/api/v1/sync/head?planId={self.plan_id}").json()
        self.assertFalse(head["exists"], head)
        self.assertTrue(head["deleted"], head)

    def test_lead_identity_head_covers_group(self) -> None:
        csrf = self._login("lead1")
        self.assertEqual(csrf, self.client.cookies.get("lpp_csrf"))
        head = self.client.get(
            "/api/v1/sync/head?course=信息技术&week=2&session=1&contentTitle=一级考证辅导2"
        ).json()
        self.assertTrue(head["exists"], head)
        self.assertEqual(head["planId"], self.plan_id)


    def test_concurrent_different_packages_settle_on_conflict(self) -> None:
        # R3-3 回归：并发推不同包时，落败方必须是 409（不能因"轮次已变但头没变"返回 422）
        previous = load_json_bytes(read_package_dir("valid-package")["plan.review.json"])
        barrier = threading.Barrier(4)
        results: list[int] = []
        lock = threading.Lock()

        def worker(index: int) -> None:
            package = self._package(2, f"并发修订-{index}", previous)
            barrier.wait()
            response = self._push(package, self.first_hash)
            with lock:
                results.append(response.status_code)

        threads = [threading.Thread(target=worker, args=(index,)) for index in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), [201, 409, 409, 409], results)


if __name__ == "__main__":
    unittest.main()
