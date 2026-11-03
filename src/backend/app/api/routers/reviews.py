# -*- coding: utf-8 -*-
"""审查中心：只读列表与详情（含证据链），不提供修改报告接口。"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.api import schemas
from app.api.deps import require_role
from app.application import review_service

router = APIRouter()


@router.get("/reviews")
def list_reviews(
    context: dict[str, Any] = Depends(require_role("teacher", "lead")),
    status: schemas.ReviewStatus | None = None,
    severity: schemas.Severity | None = None,
    teacher: str | None = None,
    from_date: date | None = Query(None, alias="dateFrom"),
    to_date: date | None = Query(None, alias="dateTo"),
    page: int = 1,
    page_size: int = Query(20, alias="pageSize"),
) -> dict[str, Any]:
    filters = {
        "status": status,
        "severity": severity,
        "teacher": teacher,
        "date_from": from_date,
        "date_to": to_date,
    }
    return review_service.list_reviews(
        context["repo"], context["user"], filters=filters, page=page, page_size=page_size
    )


@router.get("/reviews/{review_id}")
def review_detail(
    request: Request,
    review_id: int,
    context: dict[str, Any] = Depends(require_role("teacher", "lead", "admin")),
) -> dict[str, Any]:
    return review_service.review_detail(
        context["repo"],
        context["user"],
        review_id,
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )


def _client_ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))
