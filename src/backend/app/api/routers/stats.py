# -*- coding: utf-8 -*-
"""统计看板：按角色范围返回 9 项指标（含分子/分母/筛选），并支持 CSV 导出。"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import require_role
from app.application import stats_service

router = APIRouter()


def _filters(
    course: str | None,
    week: int | None,
    class_name: str | None,
    teacher: str | None,
    from_date: date | None,
    to_date: date | None,
) -> dict[str, Any]:
    return {
        "course": course,
        "week": week,
        "class": class_name,
        "teacher": teacher,
        "date_from": from_date,
        "date_to": to_date,
    }


@router.get("/stats/summary")
def stats_summary(
    context: dict[str, Any] = Depends(require_role("teacher", "lead", "admin")),
    course: str | None = None,
    week: int | None = None,
    class_name: str | None = Query(None, alias="class"),
    teacher: str | None = None,
    from_date: date | None = Query(None, alias="dateFrom"),
    to_date: date | None = Query(None, alias="dateTo"),
) -> dict[str, Any]:
    filters = _filters(course, week, class_name, teacher, from_date, to_date)
    return stats_service.summary(context["repo"], context["user"], filters=filters)


@router.get("/stats/export.csv", response_class=Response)
def stats_export_csv(
    context: dict[str, Any] = Depends(require_role("teacher", "lead", "admin")),
    course: str | None = None,
    week: int | None = None,
    class_name: str | None = Query(None, alias="class"),
    teacher: str | None = None,
    from_date: date | None = Query(None, alias="dateFrom"),
    to_date: date | None = Query(None, alias="dateTo"),
) -> Response:
    filters = _filters(course, week, class_name, teacher, from_date, to_date)
    csv_text = stats_service.export_csv(context["repo"], context["user"], filters=filters)
    return Response(
        content="\ufeff" + csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="stats-summary.csv"'},
    )
