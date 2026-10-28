# -*- coding: utf-8 -*-
"""样例库：列表与管理员上传校验。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile

from app.api.deps import require_csrf_role, require_role
from app.api.uploads import read_limited
from app.application import sample_service
from app.config import max_sample_bytes
from app.domain.errors import AppError

router = APIRouter()


@router.get("/samples")
def list_samples(
    context: dict[str, Any] = Depends(require_role("teacher", "lead", "admin")),
    course: str | None = None,
    week: int | None = None,
    session: int | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = Query(20, alias="pageSize"),
) -> dict[str, Any]:
    filters = {"course": course, "week": week, "session": session, "q": q}
    return sample_service.list_samples(
        context["repo"], filters=filters, page=page, page_size=page_size
    )


@router.post("/samples", status_code=201)
async def create_sample(
    request: Request,
    file: UploadFile = File(...),
    context: dict[str, Any] = Depends(require_csrf_role("admin")),
) -> dict[str, Any]:
    if (file.content_type or "") != "application/json":
        raise AppError("UNSUPPORTED_MEDIA", f"样例必须是 application/json：{file.content_type}")
    limit = max_sample_bytes()
    if file.size is not None and file.size > limit:
        raise AppError("PAYLOAD_TOO_LARGE", f"样例 JSON 超过 {limit} 字节")
    data = await read_limited(file)
    if len(data) > limit:
        raise AppError("PAYLOAD_TOO_LARGE", f"样例 JSON 超过 {limit} 字节")
    return sample_service.create(
        context["repo"],
        context["user"],
        data,
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )


def _client_ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))
