# -*- coding: utf-8 -*-
"""教案库规则：分页、可见范围与删除权限，纯函数。"""
from __future__ import annotations

from typing import Any

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
PAGE_MAX = 100000


def page_params(page: int | None, page_size: int | None) -> tuple[int, int, int]:
    """返回 (page, page_size, offset)，越界值收敛而不是报错。"""
    actual_page = min(max(1, int(page or 1)), PAGE_MAX)
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


def task_scope_for(user: dict[str, Any]) -> dict[str, Any]:
    """任务可见范围：管理员全部、组长本组、教师本人 + 本组（组长建的任务要能推进）。"""
    role = str(user.get("role") or "")
    if role == "admin":
        return {}
    group = str(user.get("group_name") or "").strip()
    owner_id = int(user.get("id") or 0)
    if role == "lead":
        return {"group_name": group} if group else {"owner_id": owner_id}
    if group:
        return {"owner_id": owner_id, "group_name": group}
    return {"owner_id": owner_id}


def can_view(
    role: str, user_id: int, user_group: str, owner_id: int, owner_group: str
) -> bool:
    if role == "admin":
        return True
    if int(user_id) == int(owner_id):
        return True
    if role == "lead":
        return bool(user_group) and str(user_group) == str(owner_group)
    return False


def can_delete(role: str, user_id: int, owner_id: int) -> bool:
    """教师与组长可删本人教案，管理员可删全部；组长不越组删除。"""
    if role == "admin":
        return True
    return role in {"teacher", "lead"} and int(user_id) == int(owner_id)
