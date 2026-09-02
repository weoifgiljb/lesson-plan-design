# -*- coding: utf-8 -*-
"""Playwright 截图。无 Chromium 时 skip。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import SCRIPTS_DIR  # noqa: F401
from capture_ebook import write_minimal_pdf


class TestPlaywrightCapture(unittest.TestCase):
    def test_pdf_screenshot_or_skip(self) -> None:
        try:
            from capture_ebook import capture_ebook, chromium_available
        except Exception as exc:  # pragma: no cover
            self.skipTest(str(exc))
        if not chromium_available():
            self.skipTest("Playwright Chromium 未安装")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "sample.pdf"
            write_minimal_pdf(pdf, "Hello ebook")
            out = root / "shots"
            manifest = capture_ebook(pdf, out)
            self.assertTrue(manifest["ok"])
            self.assertEqual(manifest["source"], str(pdf.resolve()))
            self.assertEqual(len(manifest["pages"]), 1)
            png = Path(manifest["pages"][0]["png"])
            self.assertTrue(png.is_file())
            self.assertGreater(png.stat().st_size, 1000)
            self.assertEqual(manifest["pages"][0]["caption"], "第1页")
