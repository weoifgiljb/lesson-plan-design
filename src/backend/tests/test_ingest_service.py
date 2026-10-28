# -*- coding: utf-8 -*-
"""入库编排：落库、幂等、并发、审计与版本链。"""
from __future__ import annotations

import threading
import unittest

from factories import build_package
from support import (
    isolated_data_dir,
    load_json_bytes,
    plugin_report,
    read_package_dir,
    tempdir,
)

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.adapters import storage
from app.application import ingest_service
from app.domain.errors import AppError


class TestIngestService(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_path = self.root / "app.db"
        self.conn = open_database(self.db_path)
        self.repo = Repo(self.conn)
        self.owner = self.repo.insert_user("teacher1", "张老师", "teacher", "hash")

    def tearDown(self) -> None:
        self.conn.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _import(self, files: dict[str, bytes]) -> ingest_service.ImportResult:
        return ingest_service.import_package(self.repo, files=files, owner_id=self.owner, actor_id=self.owner)

    def test_valid_package_creates_first_version(self) -> None:
        result = self._import(read_package_dir("valid-package"))
        self.assertTrue(result.created)
        self.assertEqual(result.version_no, 1)
        self.assertEqual(self.repo.count_versions(result.plan_id), 1)
        actions = [row["action"] for row in self.repo.list_audit()]
        self.assertIn("plan.import", actions)
        stored = self.root / "files" / "plans" / str(result.plan_id) / "1" / "plan.json"
        self.assertTrue(stored.is_file())

    def test_storage_failure_rolls_back_and_is_audited(self) -> None:
        from unittest.mock import patch

        files = read_package_dir("valid-package")
        with patch.object(storage, "write_bytes", side_effect=AppError("INTERNAL", "磁盘写入失败")):
            with self.assertRaises(AppError):
                self._import(files)
        # 事务回滚：不留下版本行，也不留下半套文件
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM plan_version").fetchone()[0], 0)
        self.assertFalse((self.root / "files" / "plans").exists())
        # 拒绝审计必须在事务外写进审计表（否则会被回滚掉）
        actions = [row["action"] for row in self.repo.list_audit()]
        self.assertIn("plan.import.rejected", actions)

    def test_duplicate_package_is_idempotent(self) -> None:
        files = read_package_dir("valid-package")
        first = self._import(files)
        second = self._import(files)
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.version_no, second.version_no)
        self.assertEqual(self.repo.count_versions(first.plan_id), 1)
        self.assertIn("plan.import.duplicate", [row["action"] for row in self.repo.list_audit()])

    def test_tampered_package_is_rejected_and_audited(self) -> None:
        with self.assertRaises(AppError) as caught:
            self._import(read_package_dir("tampered-title-package"))
        self.assertEqual(caught.exception.code, "HASH_MISMATCH")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM plan_version").fetchone()[0], 0)
        rejected = [row for row in self.repo.list_audit() if row["action"] == "plan.import.rejected"]
        self.assertEqual(len(rejected), 1)
        self.assertIn("HASH_MISMATCH", rejected[0]["detail_json"])

    def test_missing_media_is_rejected(self) -> None:
        with self.assertRaises(AppError) as caught:
            self._import(read_package_dir("missing-media-package"))
        self.assertEqual(caught.exception.code, "MEDIA_MISSING")

    def test_structure_invalid_is_rejected(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        del plan["teachingPurpose"]
        files = build_package(plan, report=plugin_report(plan))
        with self.assertRaises(AppError) as caught:
            self._import(files)
        self.assertEqual(caught.exception.code, "STRUCTURE_INVALID")

    def test_second_round_creates_second_version(self) -> None:
        files = read_package_dir("valid-package")
        first = self._import(files)
        plan = load_json_bytes(files["plan.json"])
        previous = load_json_bytes(files["plan.review.json"])
        plan["activityFlow"]["summary"] = "已修改课堂小结并复审"
        report = plugin_report(plan, round_number=2, previous_report=previous)
        second_files = build_package(plan, report=report)
        second = self._import(second_files)
        self.assertTrue(second.created)
        self.assertEqual(second.plan_id, first.plan_id)
        self.assertEqual(second.version_no, 2)
        self.assertEqual(self.repo.count_versions(first.plan_id), 2)

    def test_concurrent_import_creates_single_version(self) -> None:
        files = read_package_dir("valid-package")
        results: list[ingest_service.ImportResult] = []
        errors: list[Exception] = []
        barrier = threading.Barrier(2)

        def worker() -> None:
            connection = open_database(self.db_path)
            try:
                repo = Repo(connection)
                barrier.wait()
                results.append(ingest_service.import_package(repo, files=files, owner_id=self.owner))
            except Exception as exc:  # noqa: BLE001 - 收集线程内失败
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(self.repo.count_versions(results[0].plan_id), 1)
        self.assertEqual({item.created for item in results}, {True, False})


if __name__ == "__main__":
    unittest.main()
