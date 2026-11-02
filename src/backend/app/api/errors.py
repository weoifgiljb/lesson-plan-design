# -*- coding: utf-8 -*-
"""全后端唯一 业务异常 → HTTP 映射；错误响应不含堆栈与服务器路径。"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import ERROR_CODES, AppError

logger = logging.getLogger("lpp.errors")


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))


def _payload(code: str, message: str, details: dict[str, Any], trace_id: str) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details, "traceId": trace_id}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        trace_id = _trace_id(request)
        status = ERROR_CODES.get(exc.code, 500)
        if status >= 500:
            logger.error("app error %s trace %s", exc.code, trace_id)
        return JSONResponse(status_code=status, content=_payload(exc.code, exc.message, exc.details, trace_id))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        trace_id = _trace_id(request)
        logger.error("unhandled error trace %s: %s", trace_id, type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=_payload("INTERNAL", "服务端错误", {}, trace_id),
        )
