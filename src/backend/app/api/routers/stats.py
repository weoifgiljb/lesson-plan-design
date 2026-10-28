# -*- coding: utf-8 -*-
"""统计看板：按角色范围返回指标摘要。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_role
from app.application import stats_service

router = APIRouter()


@router.get("/stats/summary")
def stats_summary(
    context: dict[str, Any] = Depends(require_role("teacher", "lead", "admin")),
) -> dict[str, Any]:
    return stats_service.summary(context["repo"], context["user"])
