# -*- coding: utf-8 -*-
"""权限矩阵（契约驱动）：已实现接口在未登录/越权/缺 CSRF 下的表现。"""
from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from support import REPO_ROOT, isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security
from app.main import create_app

CONTRACT = REPO_ROOT / "docs" / "api" / "contract.v1.json"
PASSWORD = "Lesson2026"
ROLES = ("teacher", "lead", "admin")


def implemented_endpoints() -> list[dict]:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return [item for item in data["endpoints"] if item.get("implemented") is True]


class TestPermissionMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        connection = open_database(self.root / "app.db")
        repo = Repo(connection)
        for role in ROLES:
            repo.insert_user(f"{role}1", f"{role}用户", role, security.hash_password(PASSWORD))
        connection.close()
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _login(self, role: str) -> str:
        response = self.client.post(
            "/api/v1/auth/login", json={"username": f"{role}1", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["csrfToken"]

    def test_implemented_endpoints_declare_route_shape(self) -> None:
        endpoints = implemented_endpoints()
        self.assertTrue(endpoints)
        for item in endpoints:
            self.assertIn(item["method"], {"GET", "POST", "PUT", "PATCH", "DELETE"})
            self.assertTrue(item["path"].startswith("/api/v1/"))

    def test_unauthenticated_requests_are_401(self) -> None:
        for item in implemented_endpoints():
            if item.get("auth") is False:
                continue
            with self.subTest(endpoint=f"{item['method']} {item['path']}"):
                if item["method"] == "GET":
                    response = self.client.get(item["path"])
                else:
                    response = self.client.post(item["path"], json={})
                self.assertEqual(response.status_code, 401, response.text)

    def test_public_endpoints_are_reachable(self) -> None:
        for item in implemented_endpoints():
            if item.get("auth") is not False:
                continue
            with self.subTest(endpoint=f"{item['method']} {item['path']}"):
                if item["path"].endswith("/health"):
                    self.assertEqual(self.client.get(item["path"]).status_code, 200)
                else:
                    response = self.client.post(item["path"], json={})
                    self.assertNotEqual(response.status_code, 401)

    def test_csrf_required_when_contract_says_so(self) -> None:
        csrf_endpoints = [item for item in implemented_endpoints() if item.get("csrf") is True]
        self.assertTrue(csrf_endpoints)
        for item in csrf_endpoints:
            with self.subTest(endpoint=item["path"]):
                self._login("teacher")
                self.assertEqual(self.client.post(item["path"], json={}).status_code, 403)

    def test_each_role_can_read_own_profile(self) -> None:
        for role in ROLES:
            with self.subTest(role=role):
                self._login(role)
                response = self.client.get("/api/v1/me")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["user"]["role"], role)


if __name__ == "__main__":
    unittest.main()
