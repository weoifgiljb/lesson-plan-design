# -*- coding: utf-8 -*-
"""请求/响应 DTO：只做字段形状，不做业务判断。"""
from __future__ import annotations

from typing import Any

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain import report_rules, roles, task_rules

#: 查询参数/响应里可用的枚举：从 domain 常量派生，避免路由里再写字符串字面量
TaskStatus = Literal[tuple(sorted(task_rules.TASK_RANK))]
TaskQuadrant = Literal[tuple(sorted(task_rules.QUADRANTS))]
ReviewStatus = Literal[tuple(sorted(report_rules.ALLOWED_STATUS))]
RoleName = Literal[tuple(roles.ROLES)]
Severity = Literal["blocker", "major", "minor"]

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


class UserOut(BaseModel):
    id: int
    username: str
    displayName: str
    role: str
    roleLabel: str
    # /me 与登录响应还要带这两个字段，缺了前端会拿不到"待改密/教研组"
    mustChangePassword: bool = False
    group: str = ""


class TokenOut(BaseModel):
    accessToken: str
    tokenType: str
    expiresIn: int
    expiresAt: str
    user: UserOut


class LoginOut(TokenOut):
    """网页登录比换令牌多一个 CSRF token（Cookie 会话要用）。"""

    csrfToken: str


class AuthMeOut(BaseModel):
    user: UserOut
    auth: str



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


class TaskItem(BaseModel):
    taskId: int
    course: str
    week: int
    session: int
    title: str
    className: str = ""
    dueDate: str | None = None
    status: TaskStatus
    ownerId: int
    teacher: str | None = None
    overdue: bool = False
    createdAt: str | None = None
    quadrant: TaskQuadrant
    boardPosition: int = 0
    boardVersion: int = 0
    discardedAt: str | None = None
    discarded: bool = False
    canEdit: bool = False


class TaskPage(BaseModel):
    items: list[TaskItem]
    page: int
    pageSize: int
    total: int


class TaskBoard(BaseModel):
    items: list[TaskItem]
    total: int
    counts: dict[str, int]
    generatedAt: str


class PlanListItem(BaseModel):
    planId: int
    contentTitle: str
    course: str
    week: int
    session: int
    ownerId: int
    teacher: str | None = None
    versionNo: int | None = None
    planHash: str | None = None
    reviewStatus: str | None = None
    reviewRound: int | None = None
    versionCreatedAt: str | None = None


class PlanPage(BaseModel):
    planId: int | None = None
    items: list[PlanListItem]
    page: int = 1
    pageSize: int = 20
    total: int


class PlanVersionOut(BaseModel):
    # 版本链里还带 status/review 等字段；先保留额外键，避免 response_model 静默吞字段
    model_config = ConfigDict(extra="allow")

    versionNo: int
    planHash: str
    engineVersion: str | None = None
    createdAt: str | None = None
    # 详情接口带完整 content；版本链只有元信息，所以这里可空
    content: dict[str, Any] | None = None
    source: str | None = None
    review: dict[str, Any] | None = None


class PlanDetailOut(BaseModel):
    plan: PlanListItem
    currentVersion: PlanVersionOut | None = None
    latestReview: dict[str, Any] | None = None


class PlanVersionPage(BaseModel):
    planId: int | None = None
    items: list[PlanVersionOut]
