# -*- coding: utf-8 -*-
"""教案：契约包入库、教案库列表/详情/版本/差异与软删除。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile

from app.api.responses import error_responses
from app.adapters import archive
from app.api.deps import current_context, require_csrf_role
from app.api.uploads import ACCEPTED_TYPES, read_limited
from app.application import ingest_service, plan_service
from app.domain.errors import AppError

router = APIRouter()


@router.post(
    "/plans/import",
    status_code=201,
    responses={
        200: {"description": "同一契约包已导入，返回 duplicate=true"},
        **error_responses(
            "AUTH_REQUIRED:未登录",
            "FORBIDDEN:角色不允许",
            "CONFLICT_STALE:版本冲突（headVersion / baseHash / 差异摘要）",
            "PAYLOAD_TOO_LARGE:契约包超过上限",
            "UNSUPPORTED_MEDIA:上传类型不是 zip",
            "PAYLOAD_REJECTED:契约或结构校验失败",
        ),
    },
)
async def import_plan(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead")),
) -> dict[str, Any]:
    if (file.content_type or "") not in ACCEPTED_TYPES:
        raise AppError("UNSUPPORTED_MEDIA", f"不接受的上传类型：{file.content_type}")
    data = await read_limited(file)
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


@router.get("/plans")
def list_plans(
    context: dict[str, Any] = Depends(current_context),
    course: str | None = None,
    week: int | None = None,
    session: int | None = None,
    status: str | None = None,
    teacher: str | None = None,
    page: int = 1,
    page_size: int = Query(20, alias="pageSize"),
) -> dict[str, Any]:
    filters = {"course": course, "week": week, "session": session, "status": status, "teacher": teacher}
    return plan_service.list_plans(context["repo"], context["user"], filters=filters, page=page, page_size=page_size)


@router.get("/plans/{plan_id}")
def plan_detail(
    request: Request, plan_id: int, context: dict[str, Any] = Depends(current_context)
) -> dict[str, Any]:
    return plan_service.plan_detail(
        context["repo"], context["user"], plan_id, ip=_client_ip(request), trace_id=_trace_id(request)
    )


@router.get("/plans/{plan_id}/versions")
def plan_versions(
    request: Request, plan_id: int, context: dict[str, Any] = Depends(current_context)
) -> dict[str, Any]:
    return plan_service.plan_versions(
        context["repo"], context["user"], plan_id, ip=_client_ip(request), trace_id=_trace_id(request)
    )


@router.get("/plans/{plan_id}/diff")
def plan_diff(
    request: Request,
    plan_id: int,
    context: dict[str, Any] = Depends(current_context),
    from_version: int | None = Query(None, alias="fromVersion"),
    to_version: int | None = Query(None, alias="toVersion"),
) -> dict[str, Any]:
    return plan_service.plan_diff(
        context["repo"],
        context["user"],
        plan_id,
        from_version=from_version,
        to_version=to_version,
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )


@router.delete("/plans/{plan_id}")
def delete_plan(
    request: Request,
    plan_id: int,
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead", "admin")),
) -> dict[str, Any]:
    return plan_service.delete_plan(
        context["repo"],
        context["user"],
        plan_id,
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )


def _client_ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))
