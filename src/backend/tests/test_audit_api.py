# -*- coding: utf-8 -*-
"""审计台账与引擎版本 API：管理员/组长查询审计，管理员读引擎版本。"""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.application import audit_service
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestAuditApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        connection = open_database(self.db_file)
        self.repo = Repo(connection)
        self.teacher1 = self.repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD), "计算机")
        self.teacher2 = self.repo.insert_user("teacher2", "李老师", "teacher", security.hash_password(PASSWORD), "英语")
        self.lead1 = self.repo.insert_user("lead1", "王组长", "lead", security.hash_password(PASSWORD), "计算机")
        self.lead2 = self.repo.insert_user("lead2", "赵组长", "lead", security.hash_password(PASSWORD), "")
        self.admin = self.repo.insert_user("admin1", "管理员", "admin", security.hash_password(PASSWORD), "")
        self._seed()
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.repo.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _record(self, actor: int, action: str, target_type: str, target_id: str) -> None:
        audit_service.record(
            self.repo,
            actor_id=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail={"note": action},
            ip="127.0.0.1",
            trace_id="trace-1",
        )

    def _seed(self) -> None:
        self._record(self.teacher1, "plan.import", "plan", "1")
        self._record(self.teacher2, "plan.import", "plan", "2")
        self._record(self.admin, "user.create", "user", "7")
        audit_service.record(
            self.repo,
            actor_id=None,
            action="auth.login.failed",
            target_type="user",
            target_id="unknown",
            detail={"reason": "unknown_user"},
            ip="10.0.0.9",
            trace_id="trace-sys",
        )
        self._record(self.lead2, "plan.export", "plan", "9")

    def _login(self, username: str) -> None:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)

    def test_admin_sees_all_entries(self) -> None:
        self._login("admin1")
        body = self.client.get("/api/v1/audit").json()
        self.assertEqual(body["total"], 6)
        self.assertEqual(body["items"][0]["action"], "auth.login")
        self.assertEqual(body["items"][0]["actor"]["name"], "管理员")
        created = next(item for item in body["items"] if item["action"] == "user.create")
        self.assertEqual(created["detail"], {"note": "user.create"})
        self.assertEqual(created["traceId"], "trace-1")

    def test_lead_sees_only_own_group(self) -> None:
        self._login("lead1")
        body = self.client.get("/api/v1/audit").json()
        self.assertEqual(body["total"], 2)
        imported = next(item for item in body["items"] if item["action"] == "plan.import")
        self.assertEqual(imported["actor"]["name"], "张老师")

    def test_teacher_is_forbidden(self) -> None:
        self._login("teacher1")
        self.assertEqual(self.client.get("/api/v1/audit").status_code, 403)

    def test_filters_and_pagination(self) -> None:
        self._login("admin1")
        self.assertEqual(self.client.get("/api/v1/audit?action=plan.import").json()["total"], 2)
        self.assertEqual(self.client.get("/api/v1/audit?action=user.create").json()["total"], 1)
        self.assertEqual(self.client.get("/api/v1/audit?actor=张老师").json()["total"], 1)
        self.assertEqual(self.client.get("/api/v1/audit?targetId=2").json()["total"], 1)
        paged = self.client.get("/api/v1/audit?page=2&pageSize=2").json()
        self.assertEqual((paged["page"], paged["pageSize"], paged["total"], len(paged["items"])), (2, 2, 6, 2))

    def test_admin_sees_system_actor(self) -> None:
        self._login("admin1")
        items = self.client.get("/api/v1/audit").json()["items"]
        system = next(item for item in items if item["action"] == "auth.login.failed")
        self.assertIsNone(system["actor"]["id"])
        self.assertEqual(system["actor"]["name"], "系统")

    def test_lead_without_group_sees_only_own(self) -> None:
        self._login("lead2")
        body = self.client.get("/api/v1/audit").json()
        self.assertEqual(body["total"], 2)
        self.assertTrue(all(item["actor"]["id"] == self.lead2 for item in body["items"]))

    def test_date_filter(self) -> None:
        connection = open_database(self.db_file)
        try:
            connection.execute(
                "INSERT INTO audit_log (actor_id, action, target_type, target_id, detail_json, ip,"
                " trace_id, before_hash, after_hash, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.admin,
                    "plan.export.boundary",
                    "plan",
                    "boundary",
                    "{}",
                    "127.0.0.1",
                    "trace-boundary",
                    "",
                    "",
                    "2026-10-27T15:59:59+00:00",
                ),
            )
        finally:
            connection.close()
        self._login("admin1")
        same_day = self.client.get("/api/v1/audit?dateFrom=2026-10-27&dateTo=2026-10-27").json()
        self.assertEqual(same_day["total"], 1)
        self.assertEqual(same_day["items"][0]["action"], "plan.export.boundary")
        next_day = self.client.get("/api/v1/audit?dateFrom=2026-10-28&dateTo=2026-10-28").json()
        self.assertNotIn("plan.export.boundary", [item["action"] for item in next_day["items"]])

    def test_settings_switch_is_not_allowed(self) -> None:
        self._login("admin1")
        csrf = self.client.cookies.get("lpp_csrf")
        response = self.client.put(
            "/api/v1/settings/engine", json={"engineVersion": "0.9"}, headers={"X-CSRF-Token": csrf}
        )
        self.assertEqual(response.status_code, 405)

    def test_engine_settings_for_admin(self) -> None:
        self._login("admin1")
        body = self.client.get("/api/v1/settings/engine").json()
        self.assertTrue(body["engineAvailable"])
        self.assertEqual(body["versions"]["engineVersion"], "1.0.0")
        self.assertIn("1", body["supportedContractVersions"])
        self._login("lead1")
        self.assertEqual(self.client.get("/api/v1/settings/engine").status_code, 403)


if __name__ == "__main__":
    unittest.main()
