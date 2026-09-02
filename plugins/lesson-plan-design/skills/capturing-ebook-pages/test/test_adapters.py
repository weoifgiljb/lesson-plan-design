# -*- coding: utf-8 -*-
"""格式探测、LibreOffice 降级与 PDF 页数。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import write_flate_pages_pdf, write_pages_pdf
from capture_ebook import CaptureError, detect_kind, pdf_page_count, prepare_jobs, write_minimal_pdf


class TestAdapters(unittest.TestCase):
    def test_detect_kind(self) -> None:
        self.assertEqual(detect_kind(Path("book.PDF")), "pdf")
        self.assertEqual(detect_kind(Path("a.docx")), "docx")
        self.assertEqual(detect_kind(Path("a.pptx")), "pptx")
        self.assertEqual(detect_kind(Path("a.ppt")), "ppt")
        with self.assertRaises(CaptureError):
            detect_kind(Path("a.txt"))

    def test_ppt_without_libreoffice_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ppt = Path(tmp) / "old.ppt"
            ppt.write_bytes(b"fake")
            with self.assertRaises(CaptureError) as ctx:
                prepare_jobs(ppt, Path(tmp) / "work", soffice=None)
            self.assertIn("LibreOffice", str(ctx.exception))

    def test_pdf_page_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "one.pdf"
            write_minimal_pdf(pdf, "Hello ebook")
            self.assertEqual(pdf_page_count(pdf), 1)

    def test_pdf_page_count_when_count_precedes_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "count-first.pdf"
            write_pages_pdf(pdf, page_count=3, count_before_type=True)
            self.assertEqual(pdf_page_count(pdf), 3)

    def test_pdf_page_count_reads_flate_pages_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "flate.pdf"
            write_flate_pages_pdf(pdf, page_count=4)
            self.assertEqual(pdf_page_count(pdf), 4)
