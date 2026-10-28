# -*- coding: utf-8 -*-
"""双端同步：头版本、增量拉取与带 baseHash 的推送。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile

from app.adapters import archive
from app.api.deps import require_csrf_role, require_role
from app.api.uploads import ACCEPTED_TYPES, read_limited
from app.application import sync_service
from app.domain.errors import AppError

router = APIRouter()


@router.get("/sync/head")
def sync_head(
    context: dict[str, Any] = Depends(require_role("teacher", "lead")),
    plan_id: int | None = Query(None, alias="planId"),
    course: str | None = None,
    week: int | None = None,
    session: int | None = None,
    content_title: str | None = Query(None, alias="contentTitle"),
) -> dict[str, Any]:
    identity = {"course": course or "", "week": week, "session": session, "contentTitle": content_title}
    return sync_service.head(context["repo"], context["user"], plan_id=plan_id, identity=identity)


@router.get("/sync/pull")
def sync_pull(
    context: dict[str, Any] = Depends(require_role("teacher", "lead")),
    since: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    return sync_service.pull(context["repo"], context["user"], since=since, limit=limit)


@router.post("/sync/push", status_code=201)
async def sync_push(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    base_hash: str = Form("", alias="baseHash"),
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead")),
) -> dict[str, Any]:
    if (file.content_type or "") not in ACCEPTED_TYPES:
        raise AppError("UNSUPPORTED_MEDIA", f"不接受的上传类型：{file.content_type}")
    data = await read_limited(file)
    files = archive.read_package(data)
    result = sync_service.push(
        context["repo"],
        context["user"],
        files=files,
        package_bytes=data,
        base_hash=base_hash,
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )
    if result["duplicate"]:
        response.status_code = 200
    return result


def _client_ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))
