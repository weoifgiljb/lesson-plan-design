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

    def _create(self, **overrides):
        payload = {
            "course": "信息技术",
            "week": 2,
            "session": 1,
            "title": "一级考证辅导2",
            "className": "计算机1班",
            "dueDate": (date.today() + timedelta(days=3)).isoformat(),
        }
        payload.update(overrides)
        return self.client.post("/api/v1/tasks", json=payload, headers={"X-CSRF-Token": self.csrf})

    def test_create_conflict_and_past_due(self) -> None:
        first = self._create()
        self.assertEqual(first.status_code, 201, first.text)
        self.assertFalse(first.json()["overdue"])
        self.assertEqual(self._create().status_code, 409)
        past = self._create(title="逾期课", dueDate=(date.today() - timedelta(days=1)).isoformat())
        self.assertEqual(past.status_code, 201, past.text)
        self.assertTrue(past.json()["overdue"])

    def test_list_scope_order_and_filters(self) -> None:
        self._create(dueDate=(date.today() + timedelta(days=5)).isoformat())
        self._create(title="第二课", session=2, dueDate=(date.today() + timedelta(days=1)).isoformat())
        self._create(title="无截止课", session=3, dueDate=None)
        listing = self.client.get("/api/v1/tasks").json()
        self.assertEqual(listing["total"], 3)
        self.assertEqual([item["session"] for item in listing["items"]], [2, 1, 3])
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


if __name__ == "__main__":
    unittest.main()
