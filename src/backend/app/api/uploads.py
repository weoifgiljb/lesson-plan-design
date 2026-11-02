# -*- coding: utf-8 -*-
"""上传读取：分块限量，避免先整包进内存再判断大小。"""
from __future__ import annotations

from fastapi import UploadFile

from app.config import max_package_bytes
from app.domain.errors import AppError

CHUNK_BYTES = 1024 * 1024
ACCEPTED_TYPES = {"application/zip", "application/x-zip-compressed", "application/octet-stream", ""}


async def read_limited(file: UploadFile) -> bytes:
    limit = max_package_bytes()
    buffer = bytearray()
    while True:
        chunk = await file.read(CHUNK_BYTES)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise AppError("PAYLOAD_TOO_LARGE", f"契约包超过 {limit} 字节")
    return bytes(buffer)
