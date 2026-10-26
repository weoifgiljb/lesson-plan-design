# -*- coding: utf-8 -*-
"""zip 契约包解包与安全边界。"""
from __future__ import annotations

import io
import json
import os
import unittest
import zipfile

from factories import write_zip
from support import package_zip, tempdir

from app.adapters import archive
from app.domain.errors import AppError


class TestArchive(unittest.TestCase):
    def _zip_bytes(self, entries: list[tuple[str, bytes]]) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as handle:
            for name, data in entries:
                handle.writestr(name, data)
        return buffer.getvalue()

    def test_valid_package_is_read(self) -> None:
        files = archive.read_package(package_zip("valid-0201.zip"))
        self.assertIn("manifest.json", files)
        self.assertIn("plan.json", files)
        self.assertIn("plan.review.json", files)

    def test_zip_slip_is_rejected(self) -> None:
        with self.assertRaises(AppError) as caught:
            archive.read_package(package_zip("zip-slip.zip"))
        self.assertEqual(caught.exception.code, "PAYLOAD_REJECTED")

    def test_absolute_path_is_rejected(self) -> None:
        payload = self._zip_bytes([("manifest.json", b"{}"), ("/abs.txt", b"x")])
        with self.assertRaises(AppError) as caught:
            archive.read_package(payload)
        self.assertEqual(caught.exception.code, "PAYLOAD_REJECTED")

    def test_suffix_whitelist(self) -> None:
        payload = self._zip_bytes([("manifest.json", b"{}"), ("evil.exe", b"x")])
        with self.assertRaises(AppError) as caught:
            archive.read_package(payload)
        self.assertEqual(caught.exception.code, "PAYLOAD_REJECTED")

    def test_duplicate_entries_are_rejected(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as handle:
            handle.writestr("manifest.json", b"{}")
            handle.writestr("manifest.json", b"{}")
        with self.assertRaises(AppError) as caught:
            archive.read_package(buffer.getvalue())
        self.assertEqual(caught.exception.code, "PAYLOAD_REJECTED")

    def test_corrupt_package_is_rejected(self) -> None:
        with self.assertRaises(AppError) as caught:
            archive.read_package(b"not-a-zip")
        self.assertEqual(caught.exception.code, "PAYLOAD_REJECTED")

    def test_oversize_is_rejected(self) -> None:
        previous = os.environ.get("LPP_MAX_PACKAGE_BYTES")
        os.environ["LPP_MAX_PACKAGE_BYTES"] = "1024"
        try:
            with self.assertRaises(AppError) as caught:
                archive.read_package(package_zip("valid-0201.zip"))
        finally:
            if previous is None:
                os.environ.pop("LPP_MAX_PACKAGE_BYTES", None)
            else:
                os.environ["LPP_MAX_PACKAGE_BYTES"] = previous
        self.assertEqual(caught.exception.code, "PAYLOAD_TOO_LARGE")

    def test_read_json_reports_errors(self) -> None:
        value, error = archive.read_json({"plan.json": b"{bad"}, "plan.json")
        self.assertIsNone(value)
        self.assertIn("JSON", error or "")
        value, error = archive.read_json({}, "plan.json")
        self.assertIsNone(value)
        self.assertIn("缺少", error or "")

    def test_write_zip_helper(self) -> None:
        with tempdir() as root:
            path = write_zip(root / "pkg.zip", {"manifest.json": json.dumps({}).encode()})
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
