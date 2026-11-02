# -*- coding: utf-8 -*-
"""应用装配：traceId 中间件、错误边界、路由注册与数据库初始化。"""
from __future__ import annotations

import logging
import threading
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.adapters.db.connection import open_database
from app.api.errors import register_error_handlers
from app.api.routers import health

logger = logging.getLogger("lpp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.db = open_database()
        app.state.db_lock = threading.Lock()
    except Exception:  # noqa: BLE001 - 启动失败要让健康检查报告 down 而不是进程消失
        logger.warning("database init failed; health check will report down")
        app.state.db = None
        app.state.db_lock = threading.Lock()
    yield
    if app.state.db is not None:
        app.state.db.close()


def create_app() -> FastAPI:
    application = FastAPI(title="校标教案双端平台", version="0.1.0", lifespan=lifespan)

    @application.middleware("http")
    async def trace_middleware(request: Request, call_next):
        request.state.trace_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Trace-Id"] = request.state.trace_id
        return response

    register_error_handlers(application)
    application.include_router(health.router, prefix="/api/v1")
    return application


app = create_app()
