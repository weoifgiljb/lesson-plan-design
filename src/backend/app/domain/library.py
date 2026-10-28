# -*- coding: utf-8 -*-
"""教案库规则：分页、可见范围与删除权限，纯函数。"""
from __future__ import annotations

from typing import Any

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100


def page_params(page: int | None, page_size: int | None) -> tuple[int, int, int]:
    """返回 (page, page_size, offset)，越界值收敛而不是报错。"""
    actual_page = max(1, int(page or 1))
    actual_size = min(max(int(page_size or PAGE_SIZE_DEFAULT), 1), PAGE_SIZE_MAX)
    return actual_page, actual_size, (actual_page - 1) * actual_size


def scope_for(user: dict[str, Any]) -> dict[str, Any]:
    role = str(user.get("role") or "")
    if role == "admin":
        return {}
    if role == "lead":
        group = str(user.get("group_name") or "").strip()
        if group:
            return {"group_name": group}
    return {"owner_id": int(user.get("id") or 0)}


def can_view(
    role: str, user_id: int, user_group: str, owner_id: int, owner_group: str
) -> bool:
    if role == "admin":
        return True
    if role == "lead":
        return bool(user_group) and str(user_group) == str(owner_group)
    return int(user_id) == int(owner_id)


def can_delete(role: str, user_id: int, owner_id: int) -> bool:
    return role == "admin" or (role == "teacher" and int(user_id) == int(owner_id))
