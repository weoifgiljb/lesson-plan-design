# -*- coding: utf-8 -*-
"""电子书截图技能测试共用路径与 PDF 夹具。"""
from __future__ import annotations

import sys
import zlib
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SKILL_DIR = TEST_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def write_pdf(path: Path, objects: list[bytes]) -> Path:
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


def write_pages_pdf(path: Path, *, page_count: int, count_before_type: bool) -> Path:
    if count_before_type:
        pages = f"<< /Count {page_count} /Type /Pages /Kids [] >>".encode("ascii")
    else:
        pages = f"<< /Type /Pages /Kids [] /Count {page_count} >>".encode("ascii")
    return write_pdf(
        path,
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            pages,
        ],
    )


def write_flate_pages_pdf(path: Path, *, page_count: int) -> Path:
    payload = f"<< /Type /Pages /Count {page_count} /Kids [] >>".encode("ascii")
    compressed = zlib.compress(payload)
    stream_obj = (
        b"<< /Filter /FlateDecode /Length "
        + str(len(compressed)).encode("ascii")
        + b" >>\nstream\n"
        + compressed
        + b"\nendstream"
    )
    return write_pdf(
        path,
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            stream_obj,
        ],
    )
