# -*- coding: utf-8 -*-
"""BS-13 站内通知：逾期生成、已读隔离。"""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestNotificationsApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.connection = open_database(self.root / "app.db")
        self.repo = Repo(self.connection)
        self.teacher = self.repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD), "计算机")
        self.other = self.repo.insert_user("teacher2", "李老师", "teacher", security.hash_password(PASSWORD), "计算机")
        self.repo.insert_task("信息技术", 1, 1, "逾期任务", "25计算机1班", self.teacher, "2020-01-01")
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.connection.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _login(self, username: str) -> str:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        return str(response.json()["csrfToken"])

    def test_overdue_notification_can_be_read(self) -> None:
        csrf = self._login("teacher1")
        page = self.client.get("/api/v1/notifications").json()
        self.assertGreaterEqual(page["unread"], 1)
        overdue = next(item for item in page["items"] if item["kind"] == "task_overdue")
        self.assertIn("逾期任务", overdue["title"] + overdue["body"])
        marked = self.client.post(
            f"/api/v1/notifications/{overdue['id']}/read", headers={"X-CSRF-Token": csrf}
        )
        self.assertEqual(marked.status_code, 200, marked.text)
        unread = self.client.get("/api/v1/notifications?unreadOnly=true").json()
        self.assertNotIn(overdue["id"], [item["id"] for item in unread["items"]])
        self.client.post("/api/v1/notifications/read-all", headers={"X-CSRF-Token": csrf})
        self.assertEqual(self.client.get("/api/v1/notifications?unreadOnly=true").json()["total"], 0)

    def test_overdue_notification_uses_date_only_semantics(self) -> None:
        # due_date 是纯日期串；"今天到期"不是逾期，与 task_rules.is_overdue 保持一致
        from datetime import date, timedelta

        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        self.repo.insert_task("信息技术", 2, 1, "今天到期", "25计算机1班", self.teacher, today)
        self.repo.insert_task("信息技术", 3, 1, "昨天到期", "25计算机1班", self.teacher, yesterday)
        done = self.repo.insert_task("信息技术", 4, 1, "已导出", "25计算机1班", self.teacher, yesterday)
        self.repo.set_task_status(done, "exported")
        self._login("teacher1")
        items = self.client.get("/api/v1/notifications").json()["items"]
        bodies = " ".join(item["body"] for item in items if item["kind"] == "task_overdue")
        self.assertIn("昨天到期", bodies)
        self.assertNotIn("今天到期", bodies)
        self.assertNotIn("已导出", bodies)

    def test_notifications_are_private(self) -> None:
        self._login("teacher2")
        self.assertEqual(self.client.get("/api/v1/notifications").json()["total"], 0)


if __name__ == "__main__":
    unittest.main()
