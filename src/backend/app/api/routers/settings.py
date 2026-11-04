# -*- coding: utf-8 -*-
"""设置：引擎与模板版本查询。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_role
from app.application import settings_service

router = APIRouter()


@router.get("/settings/engine")
def engine_info(context: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    return settings_service.engine_info()
