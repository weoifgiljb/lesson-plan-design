# -*- coding: utf-8 -*-
"""权限矩阵（契约驱动）：29 个接口 × 未登录 × 3 角色。"""
from __future__ import annotations

import json
import re
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


def contract_endpoints() -> list[dict]:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return list(data["endpoints"])


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

    def _request(self, item: dict, csrf: str | None = None, client=None):
        target = client or self.client
        method = item["method"]
        # 路径参数名不统一（{id}/{sample_id}/{task_id}）：一律替换成 1，否则矩阵打不到真实路由
        path = re.sub(r"\{[^}]+\}", "1", item["path"])
        headers = {"X-CSRF-Token": csrf} if csrf else {}
        if path.endswith("/import"):
            return target.post(
                path,
                files={"file": ("probe.zip", b"not-a-zip", "application/zip")},
                headers=headers,
            )
        if path.endswith("/push"):
            return target.post(
                path,
                files={"file": ("probe.zip", b"not-a-zip", "application/zip")},
                data={"baseHash": ""},
                headers=headers,
            )
        if path.endswith("/login"):
            with TestClient(create_app()) as throwaway:
                return throwaway.post(path, json={"username": "teacher1", "password": PASSWORD})
        if method == "GET":
            return target.get(path, headers=headers)
        if method == "DELETE":
            return target.delete(path, headers=headers)
        if method == "PATCH":
            return target.patch(path, json={}, headers=headers)
        return target.post(path, json={}, headers=headers)

    def test_all_endpoints_are_covered_by_matrix(self) -> None:
        # 契约扩容时不写死数字：矩阵必须覆盖契约里的每一个端点
        paths = {(item["method"], item["path"]) for item in contract_endpoints()}
        self.assertGreaterEqual(len(paths), 33)
        # 上游审计导出端点必须仍在矩阵里（合并时不能把这条断言丢掉）
        self.assertIn(("GET", "/api/v1/audit/export"), paths)
        self.assertIn(("POST", "/api/v1/tasks/{task_id}/rollback"), paths)

    def test_unauthenticated_requests(self) -> None:
        anonymous = TestClient(create_app())
        anonymous.__enter__()
        try:
            for item in contract_endpoints():
                with self.subTest(endpoint=f"{item['method']} {item['path']}"):
                    response = self._request(item, client=anonymous)
                    if not item.get("implemented"):
                        self.assertIn(response.status_code, (404, 405), response.text)
                    elif item.get("auth") is False:
                        self.assertNotEqual(response.status_code, 401)
                    else:
                        self.assertEqual(response.status_code, 401, response.text)
        finally:
            anonymous.__exit__(None, None, None)

    def test_roles_matrix(self) -> None:
        for item in contract_endpoints():
            if not item.get("implemented") or item.get("auth") is False:
                continue
            for role in ROLES:
                with self.subTest(endpoint=f"{item['method']} {item['path']}", role=role):
                    csrf = self._login(role)
                    response = self._request(item, csrf)
                    if role in (item.get("roles") or []):
                        self.assertNotIn(response.status_code, (401, 403), response.text)
                    else:
                        self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main()
