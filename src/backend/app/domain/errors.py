# -*- coding: utf-8 -*-
"""业务异常：错误码表见 app/domain/error_codes.py，HTTP 状态由它推导。"""
from __future__ import annotations

from typing import Any

from app.domain.error_codes import ERROR_CODES  # noqa: F401 - 兼容旧引用，目录见 error_codes.py


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
