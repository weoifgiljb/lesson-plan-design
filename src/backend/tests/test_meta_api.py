# -*- coding: utf-8 -*-
"""平台元数据：前端不该自己抄状态/角色/限制，统一从 /meta 取。"""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.domain import library, report_rules, roles, task_rules, user_rules
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestMetaApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        connection = open_database(self.root / "app.db")
        connection.execute(
            "INSERT INTO user (username, display_name, role, password_hash, created_at)"
            " VALUES ('teacher1', '张老师', 'teacher', ?, datetime('now'))",
            (security.hash_password(PASSWORD),),
        )
        connection.commit()
        connection.close()
        self.client = TestClient(create_app())
        self.client.__enter__()
        self.client.post("/api/v1/auth/login", json={"username": "teacher1", "password": PASSWORD})

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def test_meta_requires_login(self) -> None:
        with TestClient(create_app()) as anonymous:
            self.assertEqual(anonymous.get("/api/v1/meta").status_code, 401)

    def test_meta_matches_backend_constants(self) -> None:
        body = self.client.get("/api/v1/meta").json()
        self.assertEqual([item["code"] for item in body["roles"]], list(roles.ROLES))
        self.assertEqual(body["roles"][0]["label"], roles.ROLE_LABELS["teacher"])
        # 任务状态顺序就是 TASK_RANK 的升序
        ranks = [item["rank"] for item in body["taskStatuses"]]
        self.assertEqual(ranks, sorted(ranks))
        # 象限与默认值来自 task_rules
        self.assertEqual({item["code"] for item in body["quadrants"]}, set(task_rules.QUADRANTS))
        self.assertEqual(body["defaultQuadrant"], task_rules.DEFAULT_QUADRANT)
        # 审查状态必须与后端白名单一致
        self.assertEqual(
            {item["code"] for item in body["reviewStatuses"]}, set(report_rules.ALLOWED_STATUS)
        )
        # 限制与后端常量一致
        limits = body["limits"]
        self.assertEqual(limits["pageSizeDefault"], library.PAGE_SIZE_DEFAULT)
        self.assertEqual(limits["pageSizeMax"], library.PAGE_SIZE_MAX)
        # R4-10：用户名/显示名长度也走 domain 常量
        self.assertEqual(limits["usernameMinLength"], user_rules.USERNAME_MIN)
        self.assertEqual(limits["usernameMaxLength"], user_rules.USERNAME_MAX)
        self.assertEqual(limits["displayNameMaxLength"], user_rules.DISPLAY_NAME_MAX)


if __name__ == "__main__":
    unittest.main()
