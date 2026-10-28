# -*- coding: utf-8 -*-
"""全后端唯一 业务异常 → HTTP 映射；错误响应不含堆栈与服务器路径。"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.errors import ERROR_CODES, AppError

logger = logging.getLogger("lpp.errors")

HTTP_CODES = {401: "AUTH_REQUIRED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "NOT_FOUND", 413: "PAYLOAD_TOO_LARGE", 415: "UNSUPPORTED_MEDIA"}


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))


def _payload(code: str, message: str, details: dict[str, Any], trace_id: str) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details, "traceId": trace_id}


def _safe_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """只保留位置与原因，丢掉请求原值，避免把口令等输入回显到响应或日志。"""
    items = []
    for error in exc.errors():
        items.append(
            {
                "loc": [str(part) for part in error.get("loc", [])],
                "msg": str(error.get("msg", "")),
                "type": str(error.get("type", "")),
            }
        )
    return items


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        trace_id = _trace_id(request)
        status = ERROR_CODES.get(exc.code, 500)
        if status >= 500:
            logger.error("app error %s trace %s", exc.code, trace_id)
        return JSONResponse(status_code=status, content=_payload(exc.code, exc.message, exc.details, trace_id))

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        trace_id = _trace_id(request)
        return JSONResponse(
            status_code=422,
            content=_payload("PAYLOAD_REJECTED", "请求参数不合法", {"errors": _safe_errors(exc)}, trace_id),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        trace_id = _trace_id(request)
        code = HTTP_CODES.get(exc.status_code, "INTERNAL")
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(code, str(exc.detail), {}, trace_id),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        trace_id = _trace_id(request)
        logger.error("unhandled error trace %s: %s", trace_id, type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=_payload("INTERNAL", "服务端错误", {}, trace_id),
        )
