# -*- coding: utf-8 -*-
"""用户规则：用户名/显示名/组名规范化与长度约束，纯函数。"""
from __future__ import annotations

from typing import Any

from app.domain.errors import AppError

#: 长度约束的**唯一来源**：DTO（api/schemas、routers/users）与 /meta 都从这里取，
#: 避免出现"契约承诺 64、domain 实际只收 40"的漂移（R4-10）
USERNAME_MIN = 3
USERNAME_MAX = 40
DISPLAY_NAME_MAX = 50
GROUP_NAME_MAX = 50


def validate(username: str, display_name: str, group_name: str) -> dict[str, str]:
    name = str(username or "").strip()
    display = str(display_name or "").strip()
    group = str(group_name or "").strip()
    if len(name) < USERNAME_MIN or len(name) > USERNAME_MAX:
        raise AppError("PAYLOAD_REJECTED", f"用户名长度需在 {USERNAME_MIN}-{USERNAME_MAX} 之间")
    if not display or len(display) > DISPLAY_NAME_MAX:
        raise AppError("PAYLOAD_REJECTED", f"显示名长度需在 1-{DISPLAY_NAME_MAX} 之间")
    if len(group) > GROUP_NAME_MAX:
        raise AppError("PAYLOAD_REJECTED", "组名过长")
    return {"username": name, "display_name": display, "group_name": group}
