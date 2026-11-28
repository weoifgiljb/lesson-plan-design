# -*- coding: utf-8 -*-
"""健康检查：数据库、磁盘、插件引擎版本。"""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.api.responses import error_responses
from app.application import health_service

router = APIRouter()


@router.get("/health", responses=error_responses("SERVICE_UNAVAILABLE:依赖不可用（数据库或磁盘）"))
def health(request: Request, response: Response) -> dict:
    state = request.app.state
    data_status = getattr(state, "data_status", {"status": "ok", "data": {}})
    warnings = list(getattr(state, "config_problems", []) or [])
    if data_status.get("status") in {"missing", "foreign", "corrupt"}:
        payload = health_service.collect(None, data_status)
        payload["checks"]["security"] = "ok" if not warnings else "degraded"
        response.status_code = 503
        return {
            "status": "degraded",
            "checks": payload["checks"],
            "versions": payload["versions"],
            "data": payload["data"],
            "configWarnings": warnings,
            "message": data_status.get("message") or "",
        }
    repo = None
    if state.db_error:
        # 启动失败的原因由 main 保存；这里不再触发异常，保持 503 错误包形状
        response.status_code = 503
        return {
            "code": "SERVICE_UNAVAILABLE",
            "message": "数据库结构未对齐，请先运行 py -3 scripts/repair_schema.py --apply",
            "details": {"reason": state.db_error},
            "traceId": str(getattr(request.state, "trace_id", "")),
        }
    factory = getattr(state, "repo_factory", None)
    if factory is not None:
        repo = factory()
    try:
        payload = health_service.collect(repo, data_status)
    finally:
        if repo is not None:
            repo.close()
    payload["checks"]["security"] = "ok" if not warnings else "degraded"
    response.status_code = 200 if payload["ok"] else 503
    return {
        "status": "ok" if payload["ok"] else "degraded",
        "checks": payload["checks"],
        "versions": payload["versions"],
        "data": payload["data"],
        "configWarnings": warnings,
    }
