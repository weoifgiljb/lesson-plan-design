# -*- coding: utf-8 -*-
"""用户管理 API：管理员列表/建号、冲突、角色校验与登录。"""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestUsersApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        connection = open_database(self.db_file)
        connection.execute(
            "INSERT INTO user (username, display_name, group_name, role, password_hash, created_at)"
            " VALUES ('admin1', '管理员', '', 'admin', ?, datetime('now'))",
            (security.hash_password(PASSWORD),),
        )
        connection.execute(
            "INSERT INTO user (username, display_name, group_name, role, password_hash, created_at)"
            " VALUES ('teacher1', '张老师', '计算机', 'teacher', ?, datetime('now'))",
            (security.hash_password(PASSWORD),),
        )
        connection.close()
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

    def _create(self, csrf: str, **overrides):
        payload = {
            "username": "teacher2",
            "displayName": "李老师",
            "role": "teacher",
            "password": "Lesson2026",
            "group": "英语",
        }
        payload.update(overrides)
        return self.client.post("/api/v1/users", json=payload, headers={"X-CSRF-Token": csrf})

    def test_admin_creates_user_and_new_user_can_login(self) -> None:
        csrf = self._login("admin1")
        response = self._create(csrf)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["username"], "teacher2")
        login = self.client.post("/api/v1/auth/login", json={"username": "teacher2", "password": "Lesson2026"})
        self.assertEqual(login.status_code, 200, login.text)
        connection = open_database(self.db_file)
        try:
            audits = connection.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'user.create'").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(audits, 1)

    def test_duplicate_and_validation(self) -> None:
        csrf = self._login("admin1")
        self.assertEqual(self._create(csrf).status_code, 201)
        self.assertEqual(self._create(csrf).status_code, 409)
        self.assertEqual(self._create(csrf, username="badrole", role="auditor").status_code, 422)
        self.assertEqual(self._create(csrf, username="weak", password="123").status_code, 422)
        # R4-10：建号接口与注册/domain 同口径（3–40、显示名 ≤50）
        self.assertEqual(self._create(csrf, username="u" * 41).status_code, 422)
        self.assertEqual(self._create(csrf, username="okname", displayName="名" * 51).status_code, 422)
        self.assertEqual(self._create(csrf, username="u" * 40).status_code, 201)

    def test_admin_lists_and_filters(self) -> None:
        csrf = self._login("admin1")
        self._create(csrf)
        listing = self.client.get("/api/v1/users").json()
        self.assertEqual(listing["total"], 3)
        self.assertEqual(self.client.get("/api/v1/users?role=teacher").json()["total"], 2)
        self.assertEqual(self.client.get("/api/v1/users?q=张").json()["total"], 1)
        paged = self.client.get("/api/v1/users?page=2&pageSize=2").json()
        self.assertEqual((paged["page"], len(paged["items"]), paged["total"]), (2, 1, 3))

    def test_teacher_is_forbidden(self) -> None:
        csrf = self._login("teacher1")
        self.assertEqual(self.client.get("/api/v1/users").status_code, 403)
        self.assertEqual(self._create(csrf).status_code, 403)


if __name__ == "__main__":
    unittest.main()
