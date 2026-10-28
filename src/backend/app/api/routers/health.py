# -*- coding: utf-8 -*-
"""健康检查：数据库、磁盘、插件引擎版本。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_repo
from app.application import health_service

router = APIRouter()


@router.get("/health")
def health(response: Response, repo=Depends(get_repo)) -> dict:
    payload = health_service.collect(repo)
    response.status_code = 200 if payload["ok"] else 503
    return {
        "status": "ok" if payload["ok"] else "degraded",
        "checks": payload["checks"],
        "versions": payload["versions"],
    }
