# -*- coding: utf-8 -*-
"""Word 排版技能测试共用路径与 PNG 夹具。"""
from __future__ import annotations

import contextlib
import shutil
import struct
import sys
import tempfile
import uuid
import zlib
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SKILL_DIR = TEST_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
SKILLS_DIR = SKILL_DIR.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


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


def png_rgba(width: int, height: int) -> bytes:
    raw = b""
    for _ in range(height):
        raw += b"\x00" + b"\x00\x00\x00\xff" * width
    compressed = zlib.compress(raw)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
