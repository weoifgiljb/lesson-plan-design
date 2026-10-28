# -*- coding: utf-8 -*-
"""健康检查：数据库、磁盘、插件引擎版本。"""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.application import health_service

router = APIRouter()


@router.get("/health", responses={503: {"description": "依赖不可用（数据库或磁盘）"}})
def health(request: Request, response: Response) -> dict:
    payload = health_service.collect(getattr(request.app.state, "db", None))
    response.status_code = 200 if payload["ok"] else 503
    return {
        "status": "ok" if payload["ok"] else "degraded",
        "checks": payload["checks"],
        "versions": payload["versions"],
    }
