# -*- coding: utf-8 -*-
"""OpenAPI `responses` 声明：从 `app.domain.error_codes` 生成，避免每个路由手写状态码。

用法：

    responses=error_responses("AUTH_REQUIRED", "FORBIDDEN:账号已停用")

`"CODE:说明"` 里的说明覆盖目录默认中文；`"CODE"` 直接用目录里的说明。
同一个 HTTP 状态由多个码命中时（如 CONFLICT_STALE / CONFLICT_DELETED 都是 409），
说明会以「；」拼接，避免后写覆盖先写。
"""
from __future__ import annotations

from typing import Any

from app.domain.error_codes import CATALOG


def error_responses(*items: str) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in items:
        code, _, custom = str(item).partition(":")
        spec = CATALOG.get(code)
        if spec is None:
            raise KeyError(f"未登记的错误码：{code}")
        status = int(spec["http"])
        description = custom.strip() or str(spec["zh"])
        existing = result.get(status)
        if existing is None:
            result[status] = {"description": description, "x-error-code": code}
            continue
        if description not in str(existing["description"]):
            existing["description"] = f"{existing['description']}；{description}"
        existing["x-error-code"] = f"{existing['x-error-code']},{code}"
    return result
