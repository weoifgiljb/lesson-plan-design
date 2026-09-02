# -*- coding: utf-8 -*-
"""格式探测、LibreOffice 降级与 PDF 页数。"""
from __future__ import annotations

import tempfile
import unittest
import zlib
from pathlib import Path

from support import write_flate_pages_pdf, write_pages_pdf, write_pdf
from capture_ebook import (
    CaptureError,
    PDF_INFLATE_MAX_BYTES,
    RenderJob,
    detect_kind,
    pdf_page_count,
    prepare_jobs,
    screenshot_full_page,
    write_minimal_pdf,
)


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

    def test_pdf_page_count_skips_image_streams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "image-count.pdf"
            fake = zlib.compress(b"<< /Type /Pages /Count 99 /Kids [] >>")
            image_stream = (
                b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
                b"/Filter /FlateDecode /Length "
                + str(len(fake)).encode("ascii")
                + b" >>\nstream\n"
                + fake
                + b"\nendstream"
            )
            write_pdf(
                pdf,
                [
                    b"<< /Type /Catalog /Pages 2 0 R >>",
                    b"<< /Type /Pages /Kids [] /Count 3 >>",
                    image_stream,
                ],
            )
            self.assertEqual(pdf_page_count(pdf), 3)

    def test_pdf_page_count_skips_large_streams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "large-stream.pdf"
            payload = zlib.compress(b"<< /Type /Pages /Count 88 /Kids [] >>")
            pad = PDF_INFLATE_MAX_BYTES + 1 - len(payload)
            raw = payload + (b"X" * max(pad, 1))
            large_stream = (
                b"<< /Filter /FlateDecode /Length "
                + str(len(raw)).encode("ascii")
                + b" >>\nstream\n"
                + raw
                + b"\nendstream"
            )
            write_pdf(
                pdf,
                [
                    b"<< /Type /Catalog /Pages 2 0 R >>",
                    b"<< /Type /Pages /Kids [] /Count 2 >>",
                    large_stream,
                ],
            )
            self.assertEqual(pdf_page_count(pdf), 2)

    def test_pdf_jobs_use_viewport_screenshot(self) -> None:
        pdf_job = RenderJob(page=1, path=Path("book.pdf"), kind="pdf")
        html_job = RenderJob(page=1, path=Path("slide.html"), kind="html")
        self.assertFalse(screenshot_full_page(pdf_job))
        self.assertTrue(screenshot_full_page(html_job))
