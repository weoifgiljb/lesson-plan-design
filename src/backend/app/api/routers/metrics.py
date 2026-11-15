# -*- coding: utf-8 -*-
"""BS-16 运维指标：导出失败率与同步冲突率。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api import schemas
from app.api.deps import current_context
from app.application import metrics_service
from app.domain.errors import AppError

router = APIRouter()


@router.get("/metrics/ops", response_model=schemas.OpsMetricsOut)
def ops_metrics(context: dict[str, Any] = Depends(current_context)) -> dict[str, Any]:
    if str(context["user"].get("role")) != "admin":
        raise AppError("FORBIDDEN", "只有管理员可以查看运维指标")
    return metrics_service.ops(context["repo"])
