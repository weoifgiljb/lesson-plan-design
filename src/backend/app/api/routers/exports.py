# -*- coding: utf-8 -*-
"""导出中心：批量创建、状态查询与产物下载。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.api.deps import require_csrf_role, require_role
from app.application import export_service

router = APIRouter()

DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ExportRequest(BaseModel):
    planVersionIds: list[int]


@router.post("/exports", status_code=201)
def create_exports(
    request: Request,
    response: Response,
    payload: ExportRequest,
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead")),
) -> dict[str, Any]:
    result = export_service.create(
        context["repo"],
        context["user"],
        payload.planVersionIds,
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )
    if result["created"] == 0 and result["reused"] > 0:
        response.status_code = 200
    return result


@router.get("/exports/{export_id}")
def export_detail(
    export_id: int, context: dict[str, Any] = Depends(require_role("teacher", "lead"))
) -> dict[str, Any]:
    return export_service.detail(context["repo"], context["user"], export_id)


@router.get("/exports/{export_id}/download")
def download_export(
    export_id: int, context: dict[str, Any] = Depends(require_role("teacher", "lead"))
) -> Response:
    payload, data = export_service.download(context["repo"], context["user"], export_id)
    filename = f'lesson-plan-v{payload["versionNo"]}.docx'
    return Response(
        content=data,
        media_type=DOCX_MEDIA,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Docx-Sha256": str(payload.get("docxSha256") or ""),
        },
    )


def _client_ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))
