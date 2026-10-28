# -*- coding: utf-8 -*-
"""用户规则：用户名/显示名/组名规范化与长度约束，纯函数。"""
from __future__ import annotations

from typing import Any

from app.domain.errors import AppError


def validate(username: str, display_name: str, group_name: str) -> dict[str, str]:
    name = str(username or "").strip()
    display = str(display_name or "").strip()
    group = str(group_name or "").strip()
    if len(name) < 3 or len(name) > 40:
        raise AppError("PAYLOAD_REJECTED", "用户名长度需在 3-40 之间")
    if not display or len(display) > 50:
        raise AppError("PAYLOAD_REJECTED", "显示名长度需在 1-50 之间")
    if len(group) > 50:
        raise AppError("PAYLOAD_REJECTED", "组名过长")
    return {"username": name, "display_name": display, "group_name": group}
