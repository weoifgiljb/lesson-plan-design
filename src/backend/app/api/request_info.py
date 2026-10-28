# -*- coding: utf-8 -*-
"""请求上下文小工具：客户端来源与 traceId，供路由、依赖与审计共用。"""
from __future__ import annotations

from fastapi import Request


def client_ip(request: Request, *, trust_forwarded: bool = False) -> str:
    if trust_forwarded:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return str(request.client.host) if request.client else ""


def trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))
