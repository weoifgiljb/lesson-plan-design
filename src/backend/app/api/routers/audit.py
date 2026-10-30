# -*- coding: utf-8 -*-
"""审计台账：管理员/组长按范围查询，只读。"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.deps import require_role
from app.api.request_info import client_ip, trace_id
from app.application import audit_service

router = APIRouter()


@router.get("/audit")
def list_audit(
    context: dict[str, Any] = Depends(require_role("admin", "lead")),
    action: str | None = None,
    actor: str | None = None,
    target_type: str | None = Query(None, alias="targetType"),
    target_id: str | None = Query(None, alias="targetId"),
    from_date: date | None = Query(None, alias="dateFrom"),
    to_date: date | None = Query(None, alias="dateTo"),
    page: int = 1,
    page_size: int = Query(20, alias="pageSize"),
) -> dict[str, Any]:
    filters = {
        "action": action,
        "actor": actor,
        "target_type": target_type,
        "target_id": target_id,
        "date_from": from_date,
        "date_to": to_date,
    }
    return audit_service.query(
        context["repo"], context["user"], filters=filters, page=page, page_size=page_size
    )


@router.get(
    "/audit/export",
    response_class=Response,
    responses={
        200: {
            "description": "审计 CSV（UTF-8 BOM；X-Total 为匹配总数，X-Truncated 表示是否截断）",
            "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}},
        },
        422: {"description": "查询参数非法"},
    },
)
def export_audit(
    request: Request,
    context: dict[str, Any] = Depends(require_role("admin", "lead")),
    action: str | None = None,
    actor: str | None = None,
    target_type: str | None = Query(None, alias="targetType"),
    target_id: str | None = Query(None, alias="targetId"),
    from_date: date | None = Query(None, alias="dateFrom"),
    to_date: date | None = Query(None, alias="dateTo"),
) -> Response:
    filters = {
        "action": action,
        "actor": actor,
        "target_type": target_type,
        "target_id": target_id,
        "date_from": from_date,
        "date_to": to_date,
    }
    csv_text, total, truncated = audit_service.export_csv(
        context["repo"], context["user"], filters=filters
    )
    audit_service.record(
        context["repo"],
        actor_id=int(context["user"]["id"]),
        action="audit.export",
        target_type="audit",
        target_id="",
        detail={
            "rows": max(csv_text.count("\n") - 1, 0),
            "total": total,
            "truncated": truncated,
            "filters": {
                "action": action,
                "actor": actor,
                "targetType": target_type,
                "targetId": target_id,
                "dateFrom": from_date.isoformat() if from_date else None,
                "dateTo": to_date.isoformat() if to_date else None,
            },
        },
        ip=client_ip(request),
        trace_id=trace_id(request),
    )
    return Response(
        content="\ufeff" + csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="audit-export.csv"',
            "X-Total": str(total),
            "X-Truncated": "true" if truncated else "false",
        },
    )
