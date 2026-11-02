# -*- coding: utf-8 -*-
"""健康检查：数据库、磁盘、插件引擎版本。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.api.responses import error_responses
from app.api.deps import get_repo
from app.application import health_service

router = APIRouter()


@router.get("/health", responses=error_responses("SERVICE_UNAVAILABLE:依赖不可用（数据库或磁盘）"))
def health(request: Request, response: Response, repo=Depends(get_repo)) -> dict:
    payload = health_service.collect(repo)
    warnings = list(getattr(request.app.state, "config_problems", []) or [])
    payload["checks"]["security"] = "ok" if not warnings else "degraded"
    response.status_code = 200 if payload["ok"] else 503
    return {
        "status": "ok" if payload["ok"] else "degraded",
        "checks": payload["checks"],
        "versions": payload["versions"],
        "configWarnings": warnings,
    }
