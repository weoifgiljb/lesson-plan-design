# -*- coding: utf-8 -*-
"""注册与 JWT 鉴权：注册、换令牌、Bearer 访问、令牌失效与角色边界。"""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters import clock
from app.adapters.db.connection import open_database
from app.config import register_max_per_hour
from app.domain import security, tokens
from app.main import create_app

PASSWORD = "Lesson2026"


class TestJwtAuth(unittest.TestCase):
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
        connection.commit()
        connection.close()
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _register(self, username: str = "newbie", password: str = PASSWORD):
        return self.client.post(
            "/api/v1/auth/register",
            json={"username": username, "displayName": "新老师", "password": password},
        )

    def _token(self, username: str = "newbie", password: str = PASSWORD) -> str:
        response = self.client.post(
            "/api/v1/auth/token", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["accessToken"]

    def _bearer(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_register_returns_token_and_user(self) -> None:
        response = self._register()
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["user"]["role"], "teacher")
        self.assertEqual(body["tokenType"], "Bearer")
        self.assertGreater(body["expiresIn"], 0)
        self.assertTrue(body["accessToken"].count(".") == 2)

    def test_register_validation(self) -> None:
        self.assertEqual(self._register(username="ab").status_code, 422)
        self.assertEqual(self._register(password="123").status_code, 422)
        self.assertEqual(self._register().status_code, 201)
        self.assertEqual(self._register().status_code, 409)

    def test_bearer_token_grants_access(self) -> None:
        self._register()
        token = self._token()
        self.client.cookies.clear()
        me = self.client.get("/api/v1/auth/me", headers=self._bearer(token))
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["auth"], "jwt")
        self.assertEqual(me.json()["user"]["username"], "newbie")
        # 不带令牌仍要 401
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)

    def test_wrong_password_and_unknown_user(self) -> None:
        self._register()
        bad = self.client.post(
            "/api/v1/auth/token", json={"username": "newbie", "password": "wrong-password"}
        )
        self.assertEqual(bad.status_code, 401, bad.text)
        missing = self.client.post(
            "/api/v1/auth/token", json={"username": "nobody", "password": PASSWORD}
        )
        self.assertEqual(missing.status_code, 401, missing.text)

    def test_forged_and_expired_tokens_are_rejected(self) -> None:
        self._register()
        token = self._token()
        forged = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=self._bearer(forged)).status_code, 401
        )
        expired = tokens.issue(
            {"sub": 1, "role": "teacher", "tv": 1, "exp": clock.timestamp() - 10}, "lpp-dev-secret-change-me"
        )
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=self._bearer(expired)).status_code, 401
        )
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers={"Authorization": "Basic abc"}).status_code,
            401,
        )

    def test_password_change_invalidates_old_token(self) -> None:
        csrf = self.client.post(
            "/api/v1/auth/login", json={"username": "admin1", "password": PASSWORD}
        ).json()["csrfToken"]
        old = self.client.post(
            "/api/v1/auth/token", json={"username": "admin1", "password": PASSWORD}
        ).json()["accessToken"]
        changed = self.client.post(
            "/api/v1/me/password",
            json={"oldPassword": PASSWORD, "newPassword": "Lesson2027"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.client.cookies.clear()
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=self._bearer(old)).status_code, 401
        )
        fresh = self.client.post(
            "/api/v1/auth/token", json={"username": "admin1", "password": "Lesson2027"}
        ).json()["accessToken"]
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=self._bearer(fresh)).status_code, 200
        )

    def test_bearer_write_skips_csrf_but_checks_role(self) -> None:
        self._register()
        token = self._token()
        token = self._complete_first_password_change(token)
        created = self.client.post(
            "/api/v1/tasks",
            json={"course": "信息技术", "week": 3, "session": 1, "title": "JWT 建课"},
            headers=self._bearer(token),
        )
        self.assertEqual(created.status_code, 201, created.text)
        denied = self.client.get("/api/v1/users", headers=self._bearer(token))
        self.assertEqual(denied.status_code, 403, denied.text)
        # Cookie 会话写操作仍要 CSRF
        csrf = self.client.post(
            "/api/v1/auth/login", json={"username": "admin1", "password": PASSWORD}
        ).json()["csrfToken"]
        self.assertTrue(csrf)
        self.client.cookies.clear()
        self.client.post("/api/v1/auth/login", json={"username": "admin1", "password": PASSWORD})
        self.assertEqual(
            self.client.post(
                "/api/v1/tasks",
                json={"course": "信息技术", "week": 4, "session": 1, "title": "无 CSRF"},
            ).status_code,
            403,
        )


    def _complete_first_password_change(self, token: str, new_password: str = "Lesson2027") -> str:
        changed = self.client.post(
            "/api/v1/me/password",
            json={"oldPassword": PASSWORD, "newPassword": new_password},
            headers=self._bearer(token),
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        fresh = changed.json().get("accessToken")
        self.assertTrue(fresh, changed.text)
        return str(fresh)

    def test_registration_requires_password_change_first(self) -> None:
        self._register()
        token = self._token()
        blocked = self.client.post(
            "/api/v1/tasks",
            json={"course": "信息技术", "week": 3, "session": 1, "title": "未改密"},
            headers=self._bearer(token),
        )
        self.assertEqual(blocked.status_code, 403, blocked.text)
        self.assertEqual(blocked.json()["code"], "PASSWORD_CHANGE_REQUIRED")
        # 身份查询仍放行
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=self._bearer(token)).status_code, 200
        )

    def test_bearer_can_change_password_and_gets_new_token(self) -> None:
        self._register()
        token = self._token()
        fresh = self._complete_first_password_change(token)
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=self._bearer(token)).status_code, 401
        )
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=self._bearer(fresh)).status_code, 200
        )

    def test_registration_ignores_group_name(self) -> None:
        response = self.client.post(
            "/api/v1/auth/register",
            json={"username": "spy1", "displayName": "新老师", "password": PASSWORD,
                  "groupName": "数学组"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        connection = open_database(self.db_file)
        try:
            row = connection.execute(
                "SELECT group_name, must_change_password FROM user WHERE username = 'spy1'"
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(row[0], "")
        self.assertEqual(int(row[1]), 1)

    def test_non_ascii_and_bad_claims_return_401(self) -> None:
        self._register()
        token = self._token()
        # httpx 不接受非 ASCII 头，直接在 domain 层验证：非法签名必须返回原因而不是抛异常
        broken = token.rsplit(".", 1)[0] + ".签名"
        payload, problem = tokens.decode(broken, "lpp-dev-secret-change-me")
        self.assertIsNone(payload)
        self.assertTrue(problem)
        bad_subject = tokens.issue(
            {"sub": {"x": 1}, "tv": 1, "iss": "lpp", "exp": clock.timestamp() + 60},
            "lpp-dev-secret-change-me",
        )
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=self._bearer(bad_subject)).status_code, 401
        )
        wrong_issuer = tokens.issue(
            {"sub": 1, "tv": 1, "iss": "other", "exp": clock.timestamp() + 60},
            "lpp-dev-secret-change-me",
        )
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=self._bearer(wrong_issuer)).status_code, 401
        )

    def test_register_rate_limit(self) -> None:
        from app.application import rate_limit

        rate_limit.reset()
        codes = []
        for index in range(register_max_per_hour() + 1):
            response = self._register(username=f"bulk{index}")
            codes.append(response.status_code)
        self.assertIn(429, codes, codes)
        rate_limit.reset()

    def test_production_requires_explicit_secret(self) -> None:
        import os

        os.environ["LPP_ENV"] = "production"
        try:
            from app.config import security_config_problems, strict_config

            self.assertTrue(strict_config())
            self.assertTrue(security_config_problems())
        finally:
            os.environ.pop("LPP_ENV", None)


    def test_must_change_password_keeps_bootstrap_endpoints(self) -> None:
        # 前端登录守卫用 /me 取身份：未改密时 /me 必须放行，否则会"登录→403→回登录"死循环
        self._register()
        token = self._token()
        self.assertEqual(
            self.client.get("/api/v1/me", headers=self._bearer(token)).status_code, 200
        )
        self.assertEqual(
            self.client.get("/api/v1/auth/me", headers=self._bearer(token)).status_code, 200
        )
        self.assertEqual(
            self.client.get("/api/v1/tasks", headers=self._bearer(token)).status_code, 403
        )
        changed = self.client.post(
            "/api/v1/me/password",
            json={"oldPassword": PASSWORD, "newPassword": "Lesson2027"},
            headers=self._bearer(token),
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertTrue(changed.json().get("accessToken"))

    def test_duplicate_username_uses_dedicated_code(self) -> None:
        self.assertEqual(self._register(username="dup1").status_code, 201)
        again = self._register(username="dup1")
        self.assertEqual(again.status_code, 409, again.text)
        self.assertEqual(again.json()["code"], "USERNAME_TAKEN")

    def test_health_exposes_dev_secret_warning(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["checks"]["security"], "degraded")
        self.assertTrue(body["configWarnings"])

if __name__ == "__main__":
    unittest.main()
