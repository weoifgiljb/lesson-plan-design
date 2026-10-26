# -*- coding: utf-8 -*-
"""平台端错误码与业务异常：错误码表是唯一来源，HTTP 状态由它推导。"""
from __future__ import annotations

from typing import Any

ERROR_CODES = {
    "AUTH_REQUIRED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT_STALE": 409,
    "HASH_MISMATCH": 422,
    "SCHEMA_UNSUPPORTED": 422,
    "STRUCTURE_INVALID": 422,
    "REPORT_INCONSISTENT": 422,
    "MEDIA_MISSING": 422,
    "PAYLOAD_REJECTED": 422,
    "PAYLOAD_TOO_LARGE": 413,
    "RATE_LIMITED": 429,
    "INTERNAL": 500,
}


class AppError(Exception):
    """业务异常：adapter/api 边界据此映射 HTTP，不在业务层拼状态码。"""

    def __init__(self, code: str, message: str = "", details: dict[str, Any] | None = None) -> None:
        if code not in ERROR_CODES:
            code = "INTERNAL"
        self.code = code
        self.message = message or code
        self.details = details or {}
        super().__init__(self.message)

    @property
    def http_status(self) -> int:
        return ERROR_CODES[self.code]
