# -*- coding: utf-8 -*-
"""文件存储：安全路径、哈希与落盘。"""
from __future__ import annotations

import unittest

from support import isolated_data_dir, tempdir

from app.adapters import storage
from app.domain.errors import AppError


class TestStorage(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()

    def tearDown(self) -> None:
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def test_safe_path_rejects_traversal_and_absolute(self) -> None:
        for bad in ("../evil.txt", "/etc/passwd", "a/../../b", ""):
            with self.subTest(path=bad):
                with self.assertRaises(AppError):
                    storage.safe_path(self.root, bad)

    def test_write_and_read_roundtrip(self) -> None:
        target = storage.write_bytes(self.root, "plans/1/1/plan.json", b"hello")
        self.assertTrue(target.is_file())
        self.assertEqual(storage.read_bytes(self.root, "plans/1/1/plan.json"), b"hello")

    def test_store_version_files_keeps_names_and_hashes(self) -> None:
        files = {"plan.json": b"{}", "media/page-003.png": b"png"}
        stored = storage.store_version_files(7, 2, files)
        self.assertEqual(stored["plan.json"], storage.sha256_bytes(b"{}"))
        self.assertTrue((self.root / "files" / "plans" / "7" / "2" / "plan.json").is_file())
        self.assertTrue((self.root / "files" / "plans" / "7" / "2" / "media" / "page-003.png").is_file())

    def test_disk_status(self) -> None:
        self.assertEqual(storage.disk_status(), "ok")


if __name__ == "__main__":
    unittest.main()
