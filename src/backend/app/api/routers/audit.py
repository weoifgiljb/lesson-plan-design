# -*- coding: utf-8 -*-
"""审计台账：管理员/组长按范围查询，只读。"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_role
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
