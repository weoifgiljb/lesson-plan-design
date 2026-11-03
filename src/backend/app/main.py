# -*- coding: utf-8 -*-
"""应用装配：traceId 中间件、错误边界、路由注册与数据库初始化。"""
from __future__ import annotations

import logging
import threading
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.api.errors import register_error_handlers
from app.config import security_config_problems, strict_config
from app.domain.errors import AppError
from app.api.routers import (
    audit,
    auth,
    exports,
    health,
    me,
    meta,
    plans,
    reviews,
    samples,
    settings,
    stats,
    sync,
    tasks,
    users,
)

logger = logging.getLogger("lpp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_lock = threading.Lock()
    app.state.db_error = ""
    problems = security_config_problems()
    app.state.config_problems = problems
    if problems and strict_config():
        raise RuntimeError("安全配置不完整：" + "；".join(problems))
    try:
        bootstrap = open_database()
        bootstrap.close()
    except Exception as exc:  # noqa: BLE001 - 启动失败要让健康检查报告 down 而不是进程消失
        # 把原因留给 /health：早期分支建的库会因为跳号迁移缺列，需要先跑 repair_schema
        app.state.db_error = f"{type(exc).__name__}: {exc}"
        logger.warning("database init failed: %s", app.state.db_error)
    # 每请求独立连接（WAL 下多连接安全），写事务仍由同一把锁串行化
    def _repo_factory() -> Repo:
        if app.state.db_error:
            raise AppError(
                "SERVICE_UNAVAILABLE",
                "数据库结构未对齐，请先运行 py -3 scripts/repair_schema.py --apply",
                {"reason": app.state.db_error},
            )
        return Repo(open_database(), app.state.db_lock)

    app.state.repo_factory = _repo_factory
    yield


def _openapi_with_bearer(application: FastAPI) -> dict[str, Any]:
    """在生成的 OpenAPI 里补上 Bearer(JWT) 安全方案，便于 /docs 直接试。"""
    schema = FastAPI.openapi(application)
    components = schema.setdefault("components", {})
    schemes = components.setdefault("securitySchemes", {})
    schemes.setdefault(
        "bearerJwt",
        {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Authorization: Bearer <accessToken>（HS256，默认 120 分钟）",
        },
    )
    return schema


def create_app() -> FastAPI:
    application = FastAPI(title="校标教案双端平台", version="0.1.0", lifespan=lifespan)
    application.openapi = lambda: _openapi_with_bearer(application)

    @application.middleware("http")
    async def trace_middleware(request: Request, call_next):
        request.state.trace_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Trace-Id"] = request.state.trace_id
        return response

    register_error_handlers(application)
    application.include_router(health.router, prefix="/api/v1")
    application.include_router(meta.router, prefix="/api/v1")
    application.include_router(auth.router, prefix="/api/v1")
    application.include_router(me.router, prefix="/api/v1")
    application.include_router(plans.router, prefix="/api/v1")
    application.include_router(reviews.router, prefix="/api/v1")
    application.include_router(sync.router, prefix="/api/v1")
    application.include_router(audit.router, prefix="/api/v1")
    application.include_router(settings.router, prefix="/api/v1")
    application.include_router(exports.router, prefix="/api/v1")
    application.include_router(stats.router, prefix="/api/v1")
    application.include_router(samples.router, prefix="/api/v1")
    application.include_router(tasks.router, prefix="/api/v1")
    application.include_router(users.router, prefix="/api/v1")
    return application


app = create_app()
