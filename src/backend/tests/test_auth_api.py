# -*- coding: utf-8 -*-
"""认证 API：登录、会话、CSRF、锁定与退出重放。"""
from __future__ import annotations

import unittest

from fastapi import Depends
from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.api.deps import require_role
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestAuthApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        connection = open_database(self.db_file)
        repo = Repo(connection)
        repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD))
        repo.insert_user("admin1", "管理员", "admin", security.hash_password(PASSWORD))
        connection.close()
        self.app = create_app()
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _login(self, username: str = "teacher1", password: str = PASSWORD):
        return self.client.post("/api/v1/auth/login", json={"username": username, "password": password})

    def _audit_actions(self) -> list[str]:
        connection = open_database(self.db_file)
        try:
            rows = Repo(connection).list_audit(200)
        finally:
            connection.close()
        return [str(row["action"]) for row in rows]

    def test_login_sets_cookies_and_returns_user(self) -> None:
        response = self._login()
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["user"]["role"], "teacher")
        self.assertTrue(body["csrfToken"])
        session_cookie = response.headers.get("set-cookie", "")
        self.assertIn("lpp_session=", session_cookie)
        self.assertIn("HttpOnly", session_cookie)
        self.assertIn("SameSite=lax", session_cookie)
        self.assertIn("lpp_csrf=", session_cookie)
        self.assertIn("auth.login", self._audit_actions())

    def test_me_requires_session(self) -> None:
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)
        self._login()
        response = self.client.get("/api/v1/me")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["username"], "teacher1")

    def test_bad_password_is_rejected(self) -> None:
        response = self._login(password="wrong-pass1")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_REQUIRED")
        self.assertIn("auth.login.failed", self._audit_actions())

    def test_lockout_after_five_failures(self) -> None:
        for _ in range(4):
            self.assertEqual(self._login(password="wrong-pass1").status_code, 401)
        locked = self._login(password="wrong-pass1")
        self.assertEqual(locked.status_code, 429)
        self.assertEqual(locked.json()["code"], "RATE_LIMITED")
        even_correct = self._login()
        self.assertEqual(even_correct.status_code, 429)

    def test_lock_expiry_resets_failed_count(self) -> None:
        connection = open_database(self.db_file)
        try:
            row = connection.execute("SELECT id FROM user WHERE username = 'teacher1'").fetchone()
            connection.execute(
                "UPDATE user SET failed_count = ?, locked_until = ? WHERE id = ?",
                (5, "2000-01-01T00:00:00+00:00", row[0]),
            )
            connection.commit()
        finally:
            connection.close()
        # 锁定期已过：错一次应回到 401（计数从 0 重新开始），而不是立刻再锁 10 分钟
        self.assertEqual(self._login(password="wrong-pass1").status_code, 401)
        # 关键回归：锁到期后正确口令必须能登录（修复前这里恒为 429，账号被永久锁死）
        ok = self._login()
        self.assertEqual(ok.status_code, 200, ok.text)

    def test_logout_requires_csrf_and_blocks_replay(self) -> None:
        login = self._login()
        token = self.client.cookies.get("lpp_session")
        self.assertTrue(token)
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 403)
        csrf = login.json()["csrfToken"]
        ok = self.client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
        self.assertEqual(ok.status_code, 200, ok.text)
        self.client.cookies.set("lpp_session", token)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)

    def test_expired_session_is_rejected(self) -> None:
        self._login()
        connection = open_database(self.db_file)
        try:
            connection.execute("UPDATE user_session SET expires_at = '2000-01-01T00:00:00+00:00'")
        finally:
            connection.close()
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)

    def test_role_dependency_denies_teacher_and_allows_admin(self) -> None:
        def probe(context: dict = Depends(require_role("admin"))) -> dict:
            return {"role": context["user"]["role"]}

        self.app.add_api_route("/api/v1/admin-probe", probe, methods=["GET"])
        self._login()
        self.assertEqual(self.client.get("/api/v1/admin-probe").status_code, 403)
        self._login("admin1")
        allowed = self.client.get("/api/v1/admin-probe")
        self.assertEqual(allowed.status_code, 200, allowed.text)


if __name__ == "__main__":
    unittest.main()
