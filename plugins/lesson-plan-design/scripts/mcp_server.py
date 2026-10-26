# -*- coding: utf-8 -*-
"""教案 MCP 入口：路径初始化 + 兼容导出，实现在 mcp_lesson 包。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import skill_scripts

sys.path.insert(0, str(skill_scripts()))
from mcp_lesson.schema import (  # noqa: E402
    SERVER_INFO,
    TOOLS,
    TYPE_CHECKS,
    _type_ok,
    _validate_tool_arguments,
)
from mcp_lesson.tools import invoke_tool  # noqa: E402
from mcp_lesson.transport import (  # noqa: E402
    call_tool as _call_tool,
    handle as _handle,
    main,
)

_dispatch_tool = invoke_tool


def call_tool(name: str, args: dict) -> dict:
    return _call_tool(name, args, dispatch=_dispatch_tool)


def handle(msg: dict):
    return _handle(msg, dispatch=_dispatch_tool)


if __name__ == "__main__":
    main()
