# -*- coding: utf-8 -*-
"""请求/响应 DTO：只做字段形状，不做业务判断。"""
from __future__ import annotations

from typing import Any

from typing import Literal

from pydantic import BaseModel, Field

from app.domain import report_rules, roles, task_rules

#: 查询参数/响应里可用的枚举：从 domain 常量派生，避免路由里再写字符串字面量
TaskStatus = Literal[tuple(sorted(task_rules.TASK_RANK))]
TaskQuadrant = Literal[tuple(sorted(task_rules.QUADRANTS))]
ReviewStatus = Literal[tuple(sorted(report_rules.ALLOWED_STATUS))]
RoleName = Literal[tuple(roles.ROLES)]

from app.domain import roles


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterPayload(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    displayName: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class TokenPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    accessToken: str
    tokenType: str
    expiresIn: int
    expiresAt: str
    user: dict[str, Any]


class AuthMeOut(BaseModel):
    user: dict[str, Any]
    auth: str


class UserOut(BaseModel):
    id: int
    username: str
    displayName: str
    role: str
    roleLabel: str


def user_payload(user: dict[str, Any]) -> dict[str, Any]:
    role = str(user.get("role") or "")
    return {
        "id": int(user.get("id") or 0),
        "username": str(user.get("username") or ""),
        "displayName": str(user.get("display_name") or ""),
        "role": role,
        "roleLabel": roles.ROLE_LABELS.get(role, role),
        # 建号/重置后为 True：前端应强制先改密（BS-05）
        "mustChangePassword": bool(user.get("must_change_password")),
    }
