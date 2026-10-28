# -*- coding: utf-8 -*-
"""统计看板：按角色范围返回 9 项指标（含分子/分母/筛选）。"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_role
from app.application import stats_service

router = APIRouter()


@router.get("/stats/summary")
def stats_summary(
    context: dict[str, Any] = Depends(require_role("teacher", "lead", "admin")),
    course: str | None = None,
    week: int | None = None,
    teacher: str | None = None,
    from_date: date | None = Query(None, alias="dateFrom"),
    to_date: date | None = Query(None, alias="dateTo"),
) -> dict[str, Any]:
    filters = {
        "course": course,
        "week": week,
        "teacher": teacher,
        "date_from": from_date,
        "date_to": to_date,
    }
    return stats_service.summary(context["repo"], context["user"], filters=filters)
