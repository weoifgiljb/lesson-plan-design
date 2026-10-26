# -*- coding: utf-8 -*-
"""MCP 错误码、异常与 JSON-RPC 错误构造。"""
from __future__ import annotations

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

def _jsonrpc_error(mid, code: int, message: str, data: dict | None = None) -> dict:
    error: dict = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": mid, "error": error}

class ToolError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        hint: str = "",
        details: dict | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.details = details or {}
