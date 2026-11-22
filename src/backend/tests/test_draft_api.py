# -*- coding: utf-8 -*-
"""草稿教案接口：任务 → 校标骨架 v1、幂等、权限与"草稿不可导出"（PreMortem T3）。"""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"
FLOW_KEYS = {
    "introduction",
    "learningGoals",
    "knowledgeLearning",
    "taskImplementation",
    "assessment",
    "summary",
    "homework",
    "reflection",
}


class TestDraftApi(unittest.TestCase):
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
        connection.close()
        self.client = TestClient(create_app())
        self.client.__enter__()
        self.csrf = self._login("teacher1")

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _login(self, username: str) -> str:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["csrfToken"]

    def _create_task(self, title: str = "一级考证辅导2", session: int = 1) -> int:
        response = self.client.post(
            "/api/v1/tasks",
            json={
                "course": "信息技术",
                "week": 2,
                "session": session,
                "title": title,
                "className": "计算机1班",
            },
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return int(response.json()["taskId"])

    def _draft(self, task_id: int, csrf: str | None = None):
        return self.client.post(
            f"/api/v1/tasks/{task_id}/draft",
            headers={"X-CSRF-Token": csrf or self.csrf},
        )

    def _db(self):
        connection = open_database(self.db_file)
        return connection, Repo(connection)

    def test_generate_draft_creates_plan_and_version(self) -> None:
        task_id = self._create_task()
        response = self._draft(task_id)
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertGreater(body["planId"], 0)
        self.assertEqual(body["versionNo"], 1)
        self.assertFalse(body["duplicate"])
        self.assertTrue(body["planHash"])

        listing = self.client.get("/api/v1/plans?course=信息技术").json()
        item = next(entry for entry in listing["items"] if entry["planId"] == body["planId"])
        self.assertIn(item.get("reviewStatus"), (None, ""))

        detail = self.client.get(f"/api/v1/plans/{body['planId']}").json()
        flow = detail["currentVersion"]["content"]["activityFlow"]
        self.assertEqual(set(flow), FLOW_KEYS)
        self.assertEqual(detail["plan"]["contentTitle"], "一级考证辅导2")
        self.assertIsNone(detail["latestReview"])

        tasks = self.client.get("/api/v1/tasks").json()["items"]
        task = next(entry for entry in tasks if entry["taskId"] == task_id)
        self.assertEqual(task["status"], "draft")

        connection, repo = self._db()
        try:
            row = connection.execute("SELECT task_id FROM plan WHERE id = ?", (body["planId"],)).fetchone()
            self.assertEqual(int(row["task_id"]), task_id)
            source = connection.execute(
                "SELECT source FROM plan_version WHERE plan_id = ?", (body["planId"],)
            ).fetchone()
            self.assertEqual(source["source"], "draft")
            actions = [entry["action"] for entry in repo.list_audit(200)]
        finally:
            connection.close()
        self.assertIn("task.draft", actions)

    def test_draft_is_idempotent(self) -> None:
        task_id = self._create_task()
        first = self._draft(task_id)
        self.assertEqual(first.status_code, 201, first.text)
        second = self._draft(task_id)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertTrue(second.json()["duplicate"])
        self.assertEqual(second.json()["planId"], first.json()["planId"])

        versions = self.client.get(f"/api/v1/plans/{first.json()['planId']}/versions").json()
        self.assertEqual(versions["total"], 1)

        connection, repo = self._db()
        try:
            actions = [entry["action"] for entry in repo.list_audit(200)]
        finally:
            connection.close()
        self.assertIn("task.draft.duplicate", actions)

    def test_draft_permissions_and_rejected_tasks(self) -> None:
        task_id = self._create_task()
        self.assertEqual(self._draft(9999).status_code, 404)
        other = self._login("teacher2")
        self.assertEqual(self._draft(task_id, other).status_code, 403)
        admin = self._login("admin1")
        self.assertEqual(self._draft(task_id, admin).status_code, 403)
        # 归属越权必须留痕（BS-06/AC-06）：403 也要有 authz.denied
        connection = open_database(self.db_file)
        try:
            actions = [row["action"] for row in Repo(connection).list_audit(200)]
        finally:
            connection.close()
        self.assertIn("authz.denied", actions)

        self.csrf = self._login("teacher1")
        discarded = self._create_task(title="废弃课", session=2)
        self.assertEqual(
            self.client.post(
                f"/api/v1/tasks/{discarded}/discard", headers={"X-CSRF-Token": self.csrf}
            ).status_code,
            200,
        )
        self.assertEqual(self._draft(discarded).status_code, 422)

    def test_group_lead_task_cannot_be_drafted_by_teacher(self) -> None:
        # 教案绑定要求任务与教案同 owner：组长的任务只能由本人生成，避免"成功但没挂上"
        lead = self._login("lead1")
        created = self.client.post(
            "/api/v1/tasks",
            json={
                "course": "信息技术",
                "week": 2,
                "session": 1,
                "title": "组长布置的课",
                "className": "计算机1班",
            },
            headers={"X-CSRF-Token": lead},
        )
        self.assertEqual(created.status_code, 201, created.text)
        task_id = int(created.json()["taskId"])
        self.csrf = self._login("teacher1")
        response = self._draft(task_id)
        self.assertEqual(response.status_code, 403, response.text)
        connection, _repo = self._db()
        try:
            plans = connection.execute(
                "SELECT COUNT(*) AS total FROM plan WHERE owner_id = 1"
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(int(plans["total"]), 0)

    def test_second_class_same_topic_is_rejected_not_silently_duplicated(self) -> None:
        # 教案身份不含班级：第二个班级的任务不能拿到第一个班级的教案
        first = self._create_task()
        plan_id = self._draft(first).json()["planId"]
        second = self.client.post(
            "/api/v1/tasks",
            json={
                "course": "信息技术",
                "week": 2,
                "session": 1,
                "title": "一级考证辅导2",
                "className": "计算机2班",
            },
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(second.status_code, 201, second.text)
        response = self._draft(int(second.json()["taskId"]))
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["details"]["planId"], plan_id)
        versions = self.client.get(f"/api/v1/plans/{plan_id}/versions").json()
        self.assertEqual(versions["total"], 1)

    def test_duplicate_repairs_missing_task_binding(self) -> None:
        task_id = self._create_task()
        plan_id = self._draft(task_id).json()["planId"]
        connection, _repo = self._db()
        try:
            connection.execute("UPDATE plan SET task_id = NULL WHERE id = ?", (plan_id,))
            connection.commit()
        finally:
            connection.close()
        response = self._draft(task_id)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["duplicate"])
        connection, _repo = self._db()
        try:
            row = connection.execute("SELECT task_id FROM plan WHERE id = ?", (plan_id,)).fetchone()
        finally:
            connection.close()
        self.assertEqual(int(row["task_id"]), task_id)

    def test_draft_cannot_be_exported_before_review(self) -> None:
        task_id = self._create_task()
        plan_id = self._draft(task_id).json()["planId"]
        connection, _repo = self._db()
        try:
            row = connection.execute(
                "SELECT id FROM plan_version WHERE plan_id = ?", (plan_id,)
            ).fetchone()
        finally:
            connection.close()
        response = self.client.post(
            "/api/v1/exports",
            json={"planVersionIds": [int(row["id"])]},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()["items"][0]
        self.assertEqual(item["status"], "failed")
        self.assertEqual(item["code"], "REPORT_INCONSISTENT")


if __name__ == "__main__":
    unittest.main()
