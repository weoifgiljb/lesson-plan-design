# -*- coding: utf-8 -*-
"""电子书截图：页码解析与适配器测试。Playwright 无 Chromium 时 skip。"""
from __future__ import annotations

import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_ebook import (
    CaptureError,
    detect_kind,
    parse_pages,
    pdf_page_count,
    prepare_jobs,
    write_minimal_pdf,
)


class TestPageSpec(unittest.TestCase):
    def test_all_pages_when_empty(self) -> None:
        self.assertEqual(parse_pages(None, 4), [1, 2, 3, 4])

    def test_range_and_list(self) -> None:
        self.assertEqual(parse_pages("3-7", 10), [3, 4, 5, 6, 7])
        self.assertEqual(parse_pages("1,3,5", 5), [1, 3, 5])
        self.assertEqual(parse_pages("2-4,7", 7), [2, 3, 4, 7])

    def test_out_of_range_raises(self) -> None:
        with self.assertRaises(CaptureError):
            parse_pages("9-12", 3)


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
            _write_pages_pdf(pdf, page_count=3, count_before_type=True)
            self.assertEqual(pdf_page_count(pdf), 3)

    def test_pdf_page_count_reads_flate_pages_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "flate.pdf"
            _write_flate_pages_pdf(pdf, page_count=4)
            self.assertEqual(pdf_page_count(pdf), 4)


class TestPlaywrightCapture(unittest.TestCase):
    def test_pdf_screenshot_or_skip(self) -> None:
        try:
            from capture_ebook import chromium_available, capture_ebook
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


def _write_pdf(path: Path, objects: list[bytes]) -> Path:
    body = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body += f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
    xref_start = len(body)
    xref = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")
    for offset in offsets[1:]:
        xref += f"{offset:010d} 00000 n \n".encode("ascii")
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
    ).encode("ascii")
    path.write_bytes(body + xref + trailer)
    return path


def _write_pages_pdf(path: Path, *, page_count: int, count_before_type: bool) -> Path:
    if count_before_type:
        pages = f"<< /Count {page_count} /Type /Pages /Kids [] >>".encode("ascii")
    else:
        pages = f"<< /Type /Pages /Kids [] /Count {page_count} >>".encode("ascii")
    return _write_pdf(
        path,
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            pages,
        ],
    )


def _write_flate_pages_pdf(path: Path, *, page_count: int) -> Path:
    payload = f"<< /Type /Pages /Count {page_count} /Kids [] >>".encode("ascii")
    compressed = zlib.compress(payload)
    stream_obj = (
        b"<< /Filter /FlateDecode /Length "
        + str(len(compressed)).encode("ascii")
        + b" >>\nstream\n"
        + compressed
        + b"\nendstream"
    )
    return _write_pdf(
        path,
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            stream_obj,
        ],
    )


if __name__ == "__main__":
    unittest.main()
