# -*- coding: utf-8 -*-
"""BS-11 删除申请：教师提交，管理员 7 个工作日内审批。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api import schemas
from app.api.deps import current_context, require_csrf_role
from app.application import deletion_service

router = APIRouter()


def _client_ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))


@router.post("/plans/{plan_id}/deletion-request", response_model=schemas.DeletionRequestOut)
def request_deletion(
    request: Request,
    plan_id: int,
    body: schemas.DeletionRequestIn,
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead")),
) -> dict[str, Any]:
    return deletion_service.request_deletion(
        context["repo"],
        context["user"],
        plan_id,
        body.reason,
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )


@router.get("/deletion-requests", response_model=schemas.DeletionPage)
def list_deletion_requests(
    request: Request,
    status: str | None = None,
    context: dict[str, Any] = Depends(current_context),
) -> dict[str, Any]:
    return deletion_service.list_requests(context["repo"], context["user"], status)


@router.post("/deletion-requests/{request_id}/resolve", response_model=schemas.DeletionRequestOut)
def resolve_deletion_request(
    request: Request,
    request_id: int,
    body: schemas.DeletionResolveIn,
    context: dict[str, Any] = Depends(require_csrf_role("admin")),
) -> dict[str, Any]:
    return deletion_service.resolve_request(
        context["repo"],
        context["user"],
        request_id,
        body.approve,
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )
