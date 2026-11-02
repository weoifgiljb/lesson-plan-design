# -*- coding: utf-8 -*-
"""应用装配、健康检查与 OpenAPI 快照一致性。"""
from __future__ import annotations

import json
import unittest

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


class TestOpenApiSnapshot(unittest.TestCase):
    def test_snapshot_matches_application(self) -> None:
        self.assertTrue(SNAPSHOT.is_file(), "运行 py -3 scripts/run_backend_gate.py --update-contract 生成快照")
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        current = create_app().openapi()
        self.assertEqual(snapshot["paths"].keys(), current["paths"].keys())


if __name__ == "__main__":
    unittest.main()
