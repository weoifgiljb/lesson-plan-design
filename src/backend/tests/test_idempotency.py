# -*- coding: utf-8 -*-
"""并发与引擎版本留痕。"""
from __future__ import annotations

import json
import threading
import unittest

from factories import build_package
from support import isolated_data_dir, load_json_bytes, plugin_report, read_package_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.application import ingest_service
from app.domain.errors import AppError


class TestIdempotency(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_path = self.root / "app.db"
        self.conn = open_database(self.db_path)
        self.repo = Repo(self.conn)
        self.owner = self.repo.insert_user("t1", "张老师", "teacher", "hash")

    def tearDown(self) -> None:
        self.conn.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def test_engine_version_is_recorded(self) -> None:
        ingest_service.import_package(
            self.repo, files=read_package_dir("valid-package"), owner_id=self.owner
        )
        row = self.conn.execute("SELECT engine_version FROM plan_version").fetchone()
        self.assertEqual(row["engine_version"], "1.0.0")

    def test_concurrent_different_reports_one_wins(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        report = plugin_report(plan)
        second_report = json.loads(json.dumps(report))
        second_report["reviewedAt"] = "2026-10-27T00:00:00+00:00"
        packages = [build_package(plan, report=report), build_package(plan, report=second_report)]
        outcomes: list[str] = []
        start = threading.Event()

        def worker(index: int) -> None:
            connection = open_database(self.db_path)
            try:
                start.wait(5)
                repo = Repo(connection)
                ingest_service.import_package(repo, files=packages[index], owner_id=self.owner)
                outcomes.append("created")
            except AppError as exc:
                outcomes.append(exc.code)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        start.set()
        for thread in threads:
            thread.join(timeout=20)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sorted(outcomes), ["CONFLICT_STALE", "created"])
        self.assertEqual(self.repo.count_versions(1), 1)


if __name__ == "__main__":
    unittest.main()
