# -*- coding: utf-8 -*-
"""用户管理：管理员列表与新建账号。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.api import schemas
from app.api.deps import require_csrf_role, require_role
from app.application import user_service

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    displayName: str
    role: str
    password: str
    group: str = ""


@router.get("/users")
def list_users(
    context: dict[str, Any] = Depends(require_role("admin")),
    role: schemas.RoleName | None = None,
    group: str | None = None,
    q: str | None = None,
    active: int | None = None,
    page: int = 1,
    page_size: int = Query(20, alias="pageSize"),
) -> dict[str, Any]:
    return user_service.list_users(
        context["repo"],
        filters={"role": role, "group": group, "q": q, "active": active},
        page=page,
        page_size=page_size,
    )


@router.post("/users", status_code=201)
def create_user(
    request: Request,
    payload: UserCreate,
    context: dict[str, Any] = Depends(require_csrf_role("admin")),
) -> dict[str, Any]:
    user_id = user_service.create_user(
        context["repo"],
        username=payload.username,
        display_name=payload.displayName,
        role=payload.role,
        password=payload.password,
        group_name=payload.group,
        actor_id=int(context["user"]["id"]),
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )
    return {"userId": user_id, "username": payload.username, "role": payload.role}


def _client_ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))
