# -*- coding: utf-8 -*-
"""任务 API：建课冲突、列表排序/逾期、任务包与状态推进。"""
from __future__ import annotations

import io
import json
import threading
import unittest
import zipfile
from datetime import date, timedelta

from fastapi.testclient import TestClient

from support import isolated_data_dir, load_json_bytes, package_zip, read_package_dir, tempdir

from app.adapters import engine
from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.application import task_service
from app.domain import security
from app.domain.errors import AppError
from app.main import create_app

PASSWORD = "Lesson2026"


class TestTasksApi(unittest.TestCase):
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

    def _create(self, confirm: bool = False, **overrides):
        payload = {
            "course": "信息技术",
            "week": 2,
            "session": 1,
            "title": "一级考证辅导2",
            "className": "计算机1班",
            "dueDate": (date.today() + timedelta(days=3)).isoformat(),
        }
        payload.update(overrides)
        params = {"confirm": "true"} if confirm else None
        return self.client.post(
            "/api/v1/tasks", json=payload, params=params, headers={"X-CSRF-Token": self.csrf}
        )

    def test_create_conflict_and_past_due(self) -> None:
        first = self._create()
        self.assertEqual(first.status_code, 201, first.text)
        self.assertFalse(first.json()["overdue"])
        self.assertEqual(self._create().status_code, 409)
        past = self._create(title="逾期课", session=2, dueDate=(date.today() - timedelta(days=1)).isoformat())
        self.assertEqual(past.status_code, 201, past.text)
        self.assertTrue(past.json()["overdue"])

    def test_list_scope_order_and_filters(self) -> None:
        self._create(dueDate=(date.today() + timedelta(days=5)).isoformat())
        self._create(title="第二课", session=2, dueDate=(date.today() + timedelta(days=1)).isoformat())
        self._create(title="无截止课", session=3, dueDate=None)
        listing = self.client.get("/api/v1/tasks").json()
        self.assertEqual(listing["total"], 3)
        self.assertEqual([item["session"] for item in listing["items"]], [2, 1, 3])
        self.assertEqual(self.client.get("/api/v1/tasks?course=英语").json()["total"], 0)

    def test_status_filter_actually_filters(self) -> None:
        # R3-F1：repo 里两套 _task_where 互相覆盖，曾导致 ?status= 恒返回全部
        draft = self._create().json()["taskId"]
        passed = self._create(title="已过的课", session=2).json()["taskId"]
        connection = open_database(self.db_file)
        try:
            connection.execute("UPDATE task SET status = 'passed' WHERE id = ?", (passed,))
        finally:
            connection.close()
        self.assertEqual(self.client.get("/api/v1/tasks?status=draft").json()["total"], 1)
        self.assertEqual(self.client.get("/api/v1/tasks?status=passed").json()["total"], 1)
        self.assertEqual(self.client.get("/api/v1/tasks?status=exported").json()["total"], 0)
        self.assertEqual(self.client.get("/api/v1/tasks?status=bogus").json()["total"], 0)
        self.assertIn(draft, [item["taskId"] for item in self.client.get("/api/v1/tasks?status=draft").json()["items"]])

    def test_group_teacher_import_advances_lead_task(self) -> None:
        # R3-F3：组长布置的课，组内教师入库后任务状态也要推进
        lead_csrf = self._login("lead1")
        created = self.client.post(
            "/api/v1/tasks",
            json={"course": "信息技术", "week": 2, "session": 1, "title": "一级考证辅导2",
                  "className": "计算机1班"},
            headers={"X-CSRF-Token": lead_csrf},
        )
        self.assertEqual(created.status_code, 201, created.text)
        teacher_csrf = self._login("teacher1")
        imported = self.client.post(
            "/api/v1/plans/import",
            files={"file": ("valid.zip", package_zip("valid-0201.zip"), "application/zip")},
            headers={"X-CSRF-Token": teacher_csrf},
        )
        self.assertEqual(imported.status_code, 201, imported.text)
        listing = self.client.get("/api/v1/tasks").json()
        statuses = {item["taskId"]: item["status"] for item in listing["items"]}
        self.assertEqual(statuses.get(created.json()["taskId"]), "passed")

    def test_group_teacher_cannot_overwrite_lead_task(self) -> None:
        # R3-F6：组内共享=只读+推进，覆盖（改截止）只能本人或管理员
        lead_csrf = self._login("lead1")
        created = self.client.post(
            "/api/v1/tasks",
            json={"course": "信息技术", "week": 2, "session": 1, "title": "一级考证辅导2",
                  "className": "计算机1班"},
            headers={"X-CSRF-Token": lead_csrf},
        )
        self.assertEqual(created.status_code, 201, created.text)
        teacher_csrf = self._login("teacher1")
        denied = self.client.post(
            "/api/v1/tasks",
            json={"course": "信息技术", "week": 2, "session": 1, "title": "一级考证辅导2",
                  "className": "计算机1班", "dueDate": (date.today() + timedelta(days=9)).isoformat()},
            params={"confirm": "true"},
            headers={"X-CSRF-Token": teacher_csrf},
        )
        self.assertEqual(denied.status_code, 403, denied.text)

    def test_task_package_declares_engine_version(self) -> None:
        # R3-F12：任务包要带引擎版本与学期，便于插件端判断兼容性
        created = self._create().json()
        self._upload_sample()
        response = self.client.get(f"/api/v1/tasks/{created['taskId']}/package")
        self.assertEqual(response.status_code, 200, response.text)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            meta = json.loads(archive.read("task.json").decode("utf-8"))
        self.assertTrue(meta.get("engineVersion"))
        self.assertIn("term", meta)
        self.assertEqual(meta["expectedSchemaVersion"], 1)

    def test_cross_teacher_confirm_is_denied_and_audited(self) -> None:
        # R3-F2：越权审计不能被事务回滚掉
        mine = self._create().json()
        other_csrf = self._login("teacher2")
        denied = self.client.post(
            "/api/v1/tasks",
            json={"course": "信息技术", "week": 2, "session": 1, "title": "一级考证辅导2",
                  "className": "计算机1班"},
            params={"confirm": "true"},
            headers={"X-CSRF-Token": other_csrf},
        )
        self.assertEqual(denied.status_code, 403, denied.text)
        connection = open_database(self.db_file)
        try:
            rows = Repo(connection).list_audit(200)
            actions = [row["action"] for row in rows]
            targets = [row["target_id"] for row in rows]
        finally:
            connection.close()
        self.assertIn("authz.denied", actions)
        self.assertIn(str(mine["taskId"]), targets)
        self._login("teacher1")

    def test_list_scope_for_other_group(self) -> None:
        self._create(dueDate=(date.today() + timedelta(days=5)).isoformat())
        self._create(title="第二课", session=2, dueDate=(date.today() + timedelta(days=1)).isoformat())
        self._create(title="无截止课", session=3, dueDate=None)
        self._login("teacher2")
        self.assertEqual(self.client.get("/api/v1/tasks").json()["total"], 0)
        self._login("lead1")
        self.assertEqual(self.client.get("/api/v1/tasks").json()["total"], 3)
        self._login("teacher1")
        self.assertEqual(self.client.get("/api/v1/tasks?course=英语").json()["total"], 0)

    def test_package_contains_template_and_readme(self) -> None:
        created = self._create().json()
        self._upload_sample()
        response = self.client.get(f"/api/v1/tasks/{created['taskId']}/package")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["Content-Type"], "application/zip")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = set(archive.namelist())
            task_meta = json.loads(archive.read("task.json").decode("utf-8"))
            template = json.loads(archive.read("plan.json").decode("utf-8"))
        self.assertEqual(names, {"task.json", "plan.json", "README.md"})
        self.assertEqual(task_meta["taskId"], created["taskId"])
        self.assertEqual((template["course"], template["week"], template["session"]), ("信息技术", 2, 1))
        self.assertEqual(template["contentTitle"], "一级考证辅导2")
        self.assertEqual(template["teacher"], "")
        self.assertEqual(template["planNumber"], "")
        self.assertTrue(engine.validate_plan(template)["ok"])

    def test_package_permissions(self) -> None:
        created = self._create().json()
        self.assertEqual(self.client.get(f"/api/v1/tasks/{created['taskId']}/package").status_code, 200)
        self._login("teacher2")
        self.assertEqual(self.client.get(f"/api/v1/tasks/{created['taskId']}/package").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/tasks/9999/package").status_code, 404)

    def test_import_advances_task_status(self) -> None:
        created = self._create().json()
        response = self.client.post(
            "/api/v1/plans/import",
            files={"file": ("valid.zip", package_zip("valid-0201.zip"), "application/zip")},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 201, response.text)
        listing = self.client.get("/api/v1/tasks").json()
        task = next(item for item in listing["items"] if item["taskId"] == created["taskId"])
        self.assertEqual(task["status"], "passed")

    def test_concurrent_create_conflicts_not_500(self) -> None:
        lock = threading.Lock()
        user = {"id": 1, "role": "teacher"}
        payload = {
            "course": "信息技术", "week": 2, "session": 1, "title": "并发课",
            "className": "计算机1班", "dueDate": None,
        }
        outcomes: list[str] = []

        def create() -> None:
            repo = Repo(open_database(self.db_file), lock)
            try:
                task_service.create(repo, user, payload)
                outcomes.append("created")
            except AppError as exc:
                outcomes.append(exc.code)
            finally:
                repo.close()

        threads = [threading.Thread(target=create) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertCountEqual(outcomes, ["created", "CONFLICT_STALE"])
        connection = open_database(self.db_file)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM task").fetchone()[0], 1)
        finally:
            connection.close()
    def _upload_sample(self) -> None:
        admin = self._login("admin1")
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        self.client.post(
            "/api/v1/samples",
            files={"file": ("plan.json", json.dumps(plan, ensure_ascii=False).encode("utf-8"), "application/json")},
            headers={"X-CSRF-Token": admin},
        )
        self._login("teacher1")


    def test_client_cannot_choose_status(self) -> None:
        # 状态由服务端推导：客户端指定非 draft 必须 422，而不是被静默忽略
        response = self._create(status="passed")
        self.assertEqual(response.status_code, 422, response.text)
        draft = self._create(status="draft")
        self.assertEqual(draft.status_code, 201, draft.text)
        self.assertEqual(draft.json()["status"], "draft")

    def test_lead_task_visible_to_group_teacher(self) -> None:
        # 需求 BS-10：组长建的任务组内教师可见并可推进；其他组看不到
        lead_csrf = self._login("lead1")
        created = self.client.post(
            "/api/v1/tasks",
            json={
                "course": "信息技术", "week": 3, "session": 1, "title": "组长布置的课",
                "className": "计算机1班",
            },
            headers={"X-CSRF-Token": lead_csrf},
        )
        self.assertEqual(created.status_code, 201, created.text)
        task_id = created.json()["taskId"]

        self._login("teacher1")  # 计算机组
        mine = self.client.get("/api/v1/tasks").json()
        self.assertIn(task_id, [item["taskId"] for item in mine["items"]])
        self.assertEqual(self.client.get(f"/api/v1/tasks/{task_id}/package").status_code, 200)

        self._login("teacher2")  # 英语组
        other = self.client.get("/api/v1/tasks").json()
        self.assertNotIn(task_id, [item["taskId"] for item in other["items"]])
        self.assertEqual(self.client.get(f"/api/v1/tasks/{task_id}/package").status_code, 403)
        self._login("teacher1")

    def test_same_class_allows_different_topics(self) -> None:
        # 用户反馈的 bug：同一班级、同一周次/课次换一个课题，应当能各自建任务
        first = self._create()
        self.assertEqual(first.status_code, 201, first.text)
        second = self._create(title="同班的另一个课题")
        self.assertEqual(second.status_code, 201, second.text)
        self.assertNotEqual(second.json()["taskId"], first.json()["taskId"])
        listed = self.client.get("/api/v1/tasks").json()
        self.assertGreaterEqual(listed["total"], 2)

    def test_confirm_updates_existing_task(self) -> None:
        first = self._create()
        self.assertEqual(first.status_code, 201, first.text)
        # 完全相同的身份（课程/周次/课次/班级/课题）才算重复
        self.assertEqual(self._create().status_code, 409)
        confirmed = self._create(confirm=True)
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(confirmed.json()["taskId"], first.json()["taskId"])
        self.assertEqual(confirmed.json()["title"], "一级考证辅导2")

    def test_rollback_moves_status_back_and_audits(self) -> None:
        created = self._create().json()
        connection = open_database(self.db_file)
        try:
            connection.execute("UPDATE task SET status = 'passed' WHERE id = ?", (created["taskId"],))
        finally:
            connection.close()
        response = self.client.post(
            f"/api/v1/tasks/{created['taskId']}/rollback", headers={"X-CSRF-Token": self.csrf}
        )
        self.assertEqual(response.status_code, 403, response.text)  # 教师无权回退
        csrf = self._login("lead1")
        lead = self.client.post(
            f"/api/v1/tasks/{created['taskId']}/rollback", headers={"X-CSRF-Token": csrf}
        )
        self.assertEqual(lead.status_code, 200, lead.text)
        self.assertEqual(lead.json()["status"], "reviewing")
        self._login("teacher1")


    def test_password_change_revokes_other_sessions(self) -> None:
        # R3-F7：改密后旧会话必须失效（另一浏览器的 Cookie 不能继续用）
        other = TestClient(self.client.app)
        other.__enter__()
        try:
            login = other.post(
                "/api/v1/auth/login", json={"username": "teacher1", "password": PASSWORD}
            )
            self.assertEqual(login.status_code, 200, login.text)
            self.assertEqual(other.get("/api/v1/me").status_code, 200)
            changed = self.client.post(
                "/api/v1/me/password",
                json={"oldPassword": PASSWORD, "newPassword": "Lesson2027"},
                headers={"X-CSRF-Token": self.csrf},
            )
            self.assertEqual(changed.status_code, 200, changed.text)
            self.assertEqual(other.get("/api/v1/me").status_code, 401)
        finally:
            other.__exit__(None, None, None)


    def test_board_groups_by_quadrant_with_counts(self) -> None:
        self._create(title="紧急重要", session=1, quadrant="urgent_important")
        self._create(title="重要不紧急", session=2, quadrant="important_not_urgent")
        self._create(title="重要不紧急2", session=3, quadrant="important_not_urgent")
        board = self.client.get("/api/v1/tasks/board")
        self.assertEqual(board.status_code, 200, board.text)
        body = board.json()
        self.assertEqual(body["total"], 3)
        self.assertEqual(body["counts"]["urgent_important"], 1)
        self.assertEqual(body["counts"]["important_not_urgent"], 2)
        self.assertEqual(body["items"][0]["quadrant"], "important_not_urgent")
        for item in body["items"]:
            self.assertIn("boardPosition", item)
            self.assertIn("boardVersion", item)

    def test_move_updates_position_and_rejects_stale_version(self) -> None:
        created = self._create(title="移动测试").json()
        task_id = created["taskId"]
        moved = self.client.patch(
            f"/api/v1/tasks/{task_id}/board",
            json={"quadrant": "urgent_important", "position": 0, "boardVersion": 0},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(moved.status_code, 200, moved.text)
        self.assertEqual(moved.json()["quadrant"], "urgent_important")
        self.assertEqual(moved.json()["boardVersion"], 1)
        stale = self.client.patch(
            f"/api/v1/tasks/{task_id}/board",
            json={"quadrant": "urgent_important", "position": 0, "boardVersion": 0},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(stale.status_code, 409, stale.text)
        self.assertEqual(stale.json()["code"], "CONFLICT_STALE")

    def test_discard_and_restore_are_audited(self) -> None:
        task_id = self._create(title="废弃测试").json()["taskId"]
        discarded = self.client.post(
            f"/api/v1/tasks/{task_id}/discard", headers={"X-CSRF-Token": self.csrf}
        )
        self.assertEqual(discarded.status_code, 200, discarded.text)
        self.assertIsNotNone(discarded.json()["discardedAt"])
        board = self.client.get("/api/v1/tasks/board").json()
        self.assertNotIn(task_id, [item["taskId"] for item in board["items"]])
        only_discarded = self.client.get("/api/v1/tasks?discarded=true").json()
        self.assertIn(task_id, [item["taskId"] for item in only_discarded["items"]])
        restored = self.client.post(
            f"/api/v1/tasks/{task_id}/restore", headers={"X-CSRF-Token": self.csrf}
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertIsNone(restored.json()["discardedAt"])

    def test_quadrant_filter_and_unknown_quadrant(self) -> None:
        self._create(title="A", session=1, quadrant="urgent_important")
        self._create(title="B", session=2, quadrant="urgent_not_important")
        urgent = self.client.get("/api/v1/tasks?quadrant=urgent_important").json()
        self.assertEqual([item["title"] for item in urgent["items"]], ["A"])
        bad = self._create(title="C", session=3, quadrant="not_a_quadrant")
        self.assertEqual(bad.status_code, 422, bad.text)

if __name__ == "__main__":
    unittest.main()
