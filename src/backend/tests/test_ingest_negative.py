# -*- coding: utf-8 -*-
"""畸形输入与版本/审校白名单：必须 422，绝不 500。"""
from __future__ import annotations

import json
import unittest
import zipfile
from io import BytesIO

from factories import build_package, rewrite_manifest, write_zip
from support import isolated_data_dir, load_json_bytes, plugin_report, read_package_dir, tempdir

from app.adapters import archive
from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.application import ingest_service
from app.domain.errors import AppError


class TestIngestNegative(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.conn = open_database(self.root / "app.db")
        self.repo = Repo(self.conn)
        self.owner = self.repo.insert_user("t1", "张老师", "teacher", "hash")

    def tearDown(self) -> None:
        self.conn.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _import(self, files: dict[str, bytes]):
        return ingest_service.import_package(self.repo, files=files, owner_id=self.owner)

    def _base_plan(self) -> dict:
        return load_json_bytes(read_package_dir("valid-package")["plan.json"])

    def test_malformed_week_returns_structure_invalid_not_500(self) -> None:
        plan = self._base_plan()
        plan["week"] = ["第二周"]
        files = build_package(plan, report=plugin_report(plan))
        with self.assertRaises(AppError) as caught:
            self._import(files)
        self.assertEqual(caught.exception.code, "STRUCTURE_INVALID")
        self.assertEqual(self.repo.count_versions(0), 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM plan_version").fetchone()[0], 0)
        rejected = [row for row in self.repo.list_audit() if row["action"] == "plan.import.rejected"]
        self.assertEqual(len(rejected), 1)

    def test_plan_not_object_is_rejected(self) -> None:
        files = read_package_dir("valid-package")
        files["plan.json"] = b"[]"
        with self.assertRaises(AppError) as caught:
            self._import(files)
        self.assertEqual(caught.exception.code, "PAYLOAD_REJECTED")

    def test_unknown_contract_version_is_rejected(self) -> None:
        plan = self._base_plan()
        files = build_package(plan, report=plugin_report(plan))
        files = rewrite_manifest(files, lambda manifest: manifest.update({"contractVersion": "9"}))
        with self.assertRaises(AppError) as caught:
            self._import(files)
        self.assertEqual(caught.exception.code, "SCHEMA_UNSUPPORTED")

    def test_invalid_independence_is_rejected(self) -> None:
        plan = self._base_plan()
        report = plugin_report(plan)
        report["independence"] = "robot"
        files = build_package(plan, report=report)
        with self.assertRaises(AppError) as caught:
            self._import(files)
        self.assertEqual(caught.exception.code, "REPORT_INCONSISTENT")

    def test_symlink_entry_is_rejected(self) -> None:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as handle:
            handle.writestr("manifest.json", json.dumps({}))
            info = zipfile.ZipInfo("media/link.png")
            info.external_attr = (0o120777 << 16)
            handle.writestr(info, b"target")
        with self.assertRaises(AppError) as caught:
            archive.read_package(buffer.getvalue())
        self.assertEqual(caught.exception.code, "PAYLOAD_REJECTED")

    def test_zip_helper_still_works(self) -> None:
        with tempdir() as root:
            path = write_zip(root / "p.zip", {"manifest.json": b"{}"})
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
