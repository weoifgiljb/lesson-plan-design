# -*- coding: utf-8 -*-
"""应用装配、健康检查与 OpenAPI 快照一致性。"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from support import REPO_ROOT, isolated_data_dir, tempdir

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
        import sqlite3

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


class TestOpenApiSnapshot(unittest.TestCase):
    def test_snapshot_matches_application(self) -> None:
        self.assertTrue(SNAPSHOT.is_file(), "运行 py -3 scripts/run_backend_gate.py --update-contract 生成快照")
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        current = create_app().openapi()
        self.assertEqual(snapshot["paths"].keys(), current["paths"].keys())


if __name__ == "__main__":
    unittest.main()
