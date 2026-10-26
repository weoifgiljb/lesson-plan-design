# -*- coding: utf-8 -*-
"""MCP stdio 传输与协议适配。"""
from __future__ import annotations

import json
import sys

from .errors import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    ToolError,
    _jsonrpc_error,
)
from .schema import SERVER_INFO, TOOLS, _validate_tool_arguments
from .tools import invoke_tool


def call_tool(name: str, args: dict, dispatch=None) -> dict:
    dispatch = dispatch or invoke_tool
    try:
        return dispatch(name, args)
    except ToolError as exc:
        payload = {
            "ok": False,
            "error": exc.message,
            "code": exc.code,
            "hint": exc.hint,
        }
        payload.update(exc.details)
        return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}
    except Exception as exc:  # noqa: BLE001 - 工具边界必须兜底，服务不能退出
        payload = {"ok": False, "error": {"code": "TOOL_ERROR", "message": str(exc)}}
        return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}


def handle(msg: dict, dispatch=None) -> dict | None:
    dispatch = dispatch or invoke_tool
    if not isinstance(msg, dict):
        return _jsonrpc_error(
            None,
            INVALID_REQUEST,
            "请求必须是 JSON 对象",
            {"code": "INVALID_REQUEST", "message": "请求必须是 JSON 对象"},
        )
    mid = msg.get("id")
    method = msg.get("method")
    if not isinstance(method, str) or not method:
        return _jsonrpc_error(
            mid,
            INVALID_REQUEST,
            "缺少 method",
            {"code": "INVALID_REQUEST", "message": "缺少 method"},
        )
    if method == "initialize":
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }
    if method == "notifications/initialized" or method == "initialized":
        return None
    if method.startswith("notifications/"):
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
        name = params.get("name")
        args = params.get("arguments") or {}
        tool = next((item for item in TOOLS if item.get("name") == name), None)
        if tool is None:
            return _jsonrpc_error(
                mid,
                METHOD_NOT_FOUND,
                "未知工具",
                {"code": "METHOD_NOT_FOUND", "message": f"未知工具：{name}"},
            )
        errors = _validate_tool_arguments(tool, args)
        if errors:
            return _jsonrpc_error(
                mid,
                INVALID_PARAMS,
                "工具参数不合法",
                {"code": "INVALID_PARAMS", "message": "工具参数不合法", "details": errors},
            )
        try:
            result = dispatch(name, args)
        except ToolError as exc:
            code = {
                "METHOD_NOT_FOUND": METHOD_NOT_FOUND,
                "INVALID_PARAMS": INVALID_PARAMS,
            }.get(exc.code, INTERNAL_ERROR)
            return _jsonrpc_error(
                mid,
                code,
                "工具执行失败",
                {"code": exc.code, "message": exc.message, "hint": exc.hint},
            )
        except Exception as exc:  # noqa: BLE001 - 单个工具失败不得终止 stdio 服务
            return _jsonrpc_error(
                mid,
                INTERNAL_ERROR,
                "工具执行失败",
                {"code": "TOOL_ERROR", "message": str(exc)},
            )
        return {"jsonrpc": "2.0", "id": mid, "result": result}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    return _jsonrpc_error(
        mid,
        METHOD_NOT_FOUND,
        "未知方法",
        {"code": "METHOD_NOT_FOUND", "message": f"未知方法：{method}"},
    )


def _write(reply: dict) -> None:
    sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            _write(
                _jsonrpc_error(
                    None,
                    PARSE_ERROR,
                    "JSON 解析失败",
                    {"code": "PARSE_ERROR", "message": str(exc)},
                )
            )
            continue
        try:
            reply = handle(msg)
        except Exception as exc:  # noqa: BLE001 - 保持 stdio 服务存活
            mid = msg.get("id") if isinstance(msg, dict) else None
            reply = _jsonrpc_error(
                mid,
                INTERNAL_ERROR,
                "内部错误",
                {"code": "TOOL_ERROR", "message": str(exc)},
            )
        if reply is not None:
            _write(reply)
