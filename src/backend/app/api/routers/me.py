# -*- coding: utf-8 -*-
"""当前用户信息与本人改密。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.responses import error_responses
from app.api import schemas
from app.api.deps import current_context, require_csrf
from app.api.request_info import client_ip, trace_id
from app.application import token_service, user_service

router = APIRouter()


class PasswordChange(BaseModel):
    oldPassword: str
    newPassword: str


@router.get("/me", responses=error_responses("AUTH_REQUIRED:未登录或会话已失效"))
def me(context: dict[str, Any] = Depends(current_context)) -> dict[str, Any]:
    return {
        "user": schemas.user_payload(context["user"]),
        "csrfToken": str(context["session"].get("csrf_token") or ""),
    }


@router.post(
    "/me/password",
    responses=error_responses(
        "AUTH_REQUIRED:原口令不正确",
        "FORBIDDEN:缺少或错误的 CSRF token",
        "PAYLOAD_REJECTED:新口令不符合强度要求",
    ),
)
def change_password(
    request: Request,
    payload: PasswordChange,
    context: dict[str, Any] = Depends(require_csrf),
) -> dict[str, Any]:
    is_jwt = context.get("auth") == "jwt"
    user_service.change_password(
        context["repo"],
        context["user"],
        old_password=payload.oldPassword,
        new_password=payload.newPassword,
        # JWT 通道没有会话可撤销；改密靠 token_version 自增让旧令牌失效
        session_id=None if is_jwt else int(context["session"]["id"]),
        ip=client_ip(request),
        trace_id=trace_id(request),
    )
    if not is_jwt:
        return {"ok": True}
    fresh = context["repo"].user_by_id(int(context["user"]["id"]))
    return {"ok": True, **token_service.issue(context["repo"], fresh or context["user"])}



