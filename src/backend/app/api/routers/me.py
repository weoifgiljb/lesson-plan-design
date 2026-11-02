# -*- coding: utf-8 -*-
"""当前用户信息与本人改密。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api import schemas
from app.api.deps import current_context, require_csrf
from app.api.request_info import client_ip, trace_id
from app.application import user_service

router = APIRouter()


class PasswordChange(BaseModel):
    oldPassword: str
    newPassword: str


@router.get("/me")
def me(context: dict[str, Any] = Depends(current_context)) -> dict[str, Any]:
    return {
        "user": schemas.user_payload(context["user"]),
        "csrfToken": str(context["session"].get("csrf_token") or ""),
    }


@router.post(
    "/me/password",
    responses={
        401: {"description": "原口令不正确"},
        403: {"description": "缺少或错误的 CSRF token"},
        422: {"description": "新口令不符合强度要求"},
    },
)
def change_password(
    request: Request,
    payload: PasswordChange,
    context: dict[str, Any] = Depends(require_csrf),
) -> dict[str, Any]:
    user_service.change_password(
        context["repo"],
        context["user"],
        old_password=payload.oldPassword,
        new_password=payload.newPassword,
        session_id=int(context["session"]["id"]),
        ip=client_ip(request),
        trace_id=trace_id(request),
    )
    return {"ok": True}
