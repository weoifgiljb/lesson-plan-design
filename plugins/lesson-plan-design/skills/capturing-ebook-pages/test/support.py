# -*- coding: utf-8 -*-
"""电子书截图技能测试共用路径与 PDF 夹具。"""
from __future__ import annotations

import contextlib
import shutil
import sys
import tempfile
import uuid
import zlib
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SKILL_DIR = TEST_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@contextlib.contextmanager
def tempdir():
    """创建可清理的临时目录，替代 ``tempfile.TemporaryDirectory``。

    与 ``lesson-plan-design/test/support.py`` 保持同一实现：``TemporaryDirectory``
    用 0700 建目录，在 Windows 沙箱与部分杀软环境下会被判为不可写，清理也会因
    删除锁失败抛 ``PermissionError``；这里显式 0o777，清理失败只忽略。
    """
    root = Path(tempfile.gettempdir()) / f"lpp-test-{uuid.uuid4().hex}"
    root.mkdir(mode=0o777)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


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
