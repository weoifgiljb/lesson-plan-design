# -*- coding: utf-8 -*-
"""教案入库：契约包上传 → 复校 → 落库；重复包返回 200。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile

from app.adapters import archive
from app.api.deps import require_csrf_role
from app.application import ingest_service
from app.config import max_package_bytes
from app.domain.errors import AppError

router = APIRouter()

ACCEPTED_TYPES = {"application/zip", "application/x-zip-compressed", "application/octet-stream", ""}
CHUNK_BYTES = 1024 * 1024


@router.post("/plans/import", status_code=201)
async def import_plan(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead")),
) -> dict[str, Any]:
    if (file.content_type or "") not in ACCEPTED_TYPES:
        raise AppError("UNSUPPORTED_MEDIA", f"不接受的上传类型：{file.content_type}")
    data = await _read_limited(file)
    files = archive.read_package(data)
    result = ingest_service.import_package(
        context["repo"],
        files=files,
        owner_id=int(context["user"]["id"]),
        actor_id=int(context["user"]["id"]),
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )
    if not result.created:
        response.status_code = 200
    return {
        "planId": result.plan_id,
        "versionNo": result.version_no,
        "reviewId": result.review_id,
        "planHash": result.plan_hash,
        "duplicate": not result.created,
    }


async def _read_limited(file: UploadFile) -> bytes:
    """分块读取并在超过上限时立即中止，避免先整包进内存再判断。"""
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


def _client_ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))
