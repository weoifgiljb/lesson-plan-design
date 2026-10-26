# -*- coding: utf-8 -*-
"""角色与资源归属判定：纯函数，越权判定与 HTTP 解耦。"""
from __future__ import annotations

ROLES = ("teacher", "lead", "admin")
ROLE_LABELS = {"teacher": "任课教师", "lead": "教研组长", "admin": "系统管理员"}


def is_valid_role(role: str) -> bool:
    return role in ROLES


def can_access_owner(role: str, user_id: int, owner_id: int) -> bool:
    """是否可读取/操作归属某人的资源。组长按组共享的范围随 BS-02 引入。"""
    if role == "admin":
        return True
    return int(user_id) == int(owner_id)


def can_export(role: str) -> bool:
    return role in {"teacher", "lead", "admin"}


def allowed(role: str, roles: tuple[str, ...]) -> bool:
    return role in roles
