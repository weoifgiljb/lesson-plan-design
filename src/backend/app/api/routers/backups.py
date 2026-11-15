# -*- coding: utf-8 -*-
"""OPS-08 管理端备份/恢复：仅管理员，创建/恢复带 CSRF 与二次确认。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from app.api import schemas
from app.api.deps import current_context, require_csrf_role
from app.application import backup_service
from app.domain.errors import AppError

router = APIRouter()


def _ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))


@router.get("/admin/backups", response_model=schemas.BackupPage)
def list_backups(context: dict[str, Any] = Depends(current_context)) -> dict[str, Any]:
    if str(context["user"].get("role")) != "admin":
        raise AppError("FORBIDDEN", "只有管理员可以查看备份")
    return backup_service.list_snapshots()


@router.post("/admin/backups", response_model=schemas.BackupOut)
def create_backup(
    request: Request,
    body: schemas.BackupCreateIn,
    context: dict[str, Any] = Depends(require_csrf_role("admin")),
) -> dict[str, Any]:
    backup_service.create(context["repo"], context["user"], body.label, ip=_ip(request), trace_id=_trace(request))
    return backup_service.list_snapshots()["items"][0]


@router.get("/admin/backups/{name}/download")
def download_backup(
    name: str, context: dict[str, Any] = Depends(current_context)
) -> FileResponse:
    if str(context["user"].get("role")) != "admin":
        raise AppError("FORBIDDEN", "只有管理员可以下载备份")
    path, filename = backup_service.archive(name)
    return FileResponse(path, media_type="application/zip", filename=filename)


@router.post("/admin/backups/{name}/restore")
def restore_backup(
    request: Request,
    name: str,
    body: schemas.BackupRestoreIn,
    context: dict[str, Any] = Depends(require_csrf_role("admin")),
) -> dict[str, Any]:
    if not body.confirm:
        raise AppError("PAYLOAD_REJECTED", "恢复需要二次确认 confirm=true")
    return backup_service.restore(context["repo"], context["user"], name, ip=_ip(request), trace_id=_trace(request))
