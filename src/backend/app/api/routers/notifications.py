# -*- coding: utf-8 -*-
"""BS-13 站内通知与待办。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api import schemas
from app.api.deps import current_context, require_csrf_role
from app.application import notification_service

router = APIRouter()


@router.get("/notifications", response_model=schemas.NotificationPage)
def list_notifications(
    context: dict[str, Any] = Depends(current_context),
    unread_only: bool = Query(False, alias="unreadOnly"),
    page: int = 1,
    page_size: int = Query(20, alias="pageSize"),
) -> dict[str, Any]:
    limit = max(1, min(int(page_size), 100))
    offset = max(0, (max(1, int(page)) - 1) * limit)
    return notification_service.list_notifications(
        context["repo"], context["user"], unread_only=unread_only, limit=limit, offset=offset
    )


@router.post("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead", "admin")),
) -> dict[str, Any]:
    return notification_service.mark_read(context["repo"], context["user"], notification_id)


@router.post("/notifications/read-all")
def mark_all_read(
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead", "admin")),
) -> dict[str, Any]:
    return notification_service.mark_all_read(context["repo"], context["user"])
