# -*- coding: utf-8 -*-
"""应用装配、健康检查与 OpenAPI 快照一致性。"""
from __future__ import annotations

import json
import os
import sqlite3
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from support import REPO_ROOT, isolated_data_dir, tempdir

from app.adapters.db import instance
from app.main import create_app

SNAPSHOT = REPO_ROOT / "docs" / "api" / "openapi.v1.json"


class TestHealth(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.app = create_app()
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def test_health_reports_checks_and_trace(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["checks"]["database"], "ok")
        self.assertEqual(body["checks"]["engine"], "ok")
        self.assertTrue(response.headers.get("X-Trace-Id"))


class TestHealthOnBrokenDatabase(unittest.TestCase):
    def test_structure_mismatch_reports_503_with_hint(self) -> None:
        # 旧库/版本错配时不能全站 500：健康检查与业务接口都应 503 并给修复指引
        with tempdir() as root:
            env = isolated_data_dir(Path(root))
            env.__enter__()
            try:
                db = Path(root) / "app.db"
                conn = sqlite3.connect(db)
                conn.execute("PRAGMA user_version=99")
                conn.execute("CREATE TABLE t (id INTEGER)")
                conn.commit()
                conn.close()
                with TestClient(create_app(), raise_server_exceptions=False) as client:
                    health = client.get("/api/v1/health")
                    self.assertEqual(health.status_code, 503, health.text)
                    self.assertEqual(health.json()["code"], "SERVICE_UNAVAILABLE")
                    self.assertIn("repair_schema.py", health.json()["message"])
                    tasks = client.get("/api/v1/tasks")
                    self.assertEqual(tasks.status_code, 503, tasks.text)
            finally:
                env.__exit__(None, None, None)


class TestInstanceStartup(unittest.TestCase):
    def test_marker_without_database_is_not_silently_recreated(self) -> None:
        with tempdir() as root, isolated_data_dir(Path(root)):
            instance.write_instance(Path(root), 13)
            with TestClient(create_app(), raise_server_exceptions=False) as client:
                body = client.get("/api/v1/health").json()
            self.assertFalse((Path(root) / "app.db").exists())
            self.assertEqual(body["status"], "degraded")
            self.assertEqual(body["checks"]["data"], "missing")
            self.assertTrue(body["data"]["instanceId"])
            self.assertEqual(body["data"]["dir"], Path(root).name)
            self.assertNotIn(str(Path(root).resolve()), json.dumps(body, ensure_ascii=False))

    def test_nonempty_directory_without_marker_is_foreign(self) -> None:
        with tempdir() as root, isolated_data_dir(Path(root)):
            (Path(root) / "junk.txt").write_text("x", encoding="utf-8")
            with TestClient(create_app(), raise_server_exceptions=False) as client:
                body = client.get("/api/v1/health").json()
            self.assertFalse((Path(root) / "app.db").exists())
            self.assertEqual(body["checks"]["data"], "foreign")

    def test_allow_init_is_explicit_escape_hatch(self) -> None:
        with tempdir() as root, isolated_data_dir(Path(root)):
            (Path(root) / "junk.txt").write_text("x", encoding="utf-8")
            previous = os.environ.get("LPP_ALLOW_INIT")
            os.environ["LPP_ALLOW_INIT"] = "1"
            try:
                with TestClient(create_app(), raise_server_exceptions=False) as client:
                    body = client.get("/api/v1/health").json()
            finally:
                if previous is None:
                    os.environ.pop("LPP_ALLOW_INIT", None)
                else:
                    os.environ["LPP_ALLOW_INIT"] = previous
            self.assertEqual(body["status"], "ok")
            self.assertEqual(body["checks"]["data"], "ok")
            self.assertTrue((Path(root) / "app.db").is_file())
            self.assertTrue((Path(root) / ".instance.json").is_file())

    def test_new_empty_directory_writes_marker(self) -> None:
        with tempdir() as root, isolated_data_dir(Path(root)):
            with TestClient(create_app(), raise_server_exceptions=False) as client:
                body = client.get("/api/v1/health").json()
            self.assertEqual(body["status"], "ok")
            self.assertEqual(body["checks"]["data"], "ok")
            self.assertTrue((Path(root) / ".instance.json").is_file())


class TestOpenApiSnapshot(unittest.TestCase):
    def test_snapshot_matches_application(self) -> None:
        self.assertTrue(SNAPSHOT.is_file(), "运行 py -3 scripts/run_backend_gate.py --update-contract 生成快照")
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        current = create_app().openapi()
        # 深比较：路径、参数、状态码、schema、securitySchemes 漂移都要被发现
        self.assertEqual(snapshot, current)


if __name__ == "__main__":
    unittest.main()
