# -*- coding: utf-8 -*-
"""登录、退出：登录公开，退出要求会话 + CSRF。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from app.api import schemas
from app.api.request_info import client_ip, trace_id
from app.api.deps import (
    clear_session_cookie,
    current_context as require_context,
    get_repo,
    require_csrf,
    set_session_cookie,
)
from app.application import audit_service, session_service, token_service, user_service

router = APIRouter()


@router.post(
    "/auth/login",
    responses={
        401: {"description": "用户名或口令错误"},
        403: {"description": "账号已停用"},
        422: {"description": "请求体校验失败"},
        429: {"description": "连续失败次数过多，账号锁定中"},
    },
)
def login(
    payload: schemas.LoginPayload, request: Request, response: Response, repo=Depends(get_repo)
) -> dict[str, Any]:
    user, token, csrf_token = user_service.login(
        repo,
        payload.username,
        payload.password,
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )
    set_session_cookie(response, token, csrf_token)
    return {
        "user": schemas.user_payload(user),
        "csrfToken": csrf_token,
        **token_service.issue(repo, user),
    }


@router.post(
    "/auth/logout",
    responses={
        401: {"description": "未登录或会话已失效"},
        403: {"description": "缺少或错误的 CSRF token"},
    },
)
def logout(
    request: Request, response: Response, context: dict[str, Any] = Depends(require_csrf)
) -> dict[str, Any]:
    if context.get("auth") == "jwt":
        # 无状态令牌：服务端没有可撤销的会话，客户端丢弃 token 即可
        return {"ok": True}
    session_service.revoke(context["repo"], int(context["session"]["id"]))
    audit_service.record(
        context["repo"],
        actor_id=int(context["user"]["id"]),
        action="auth.logout",
        target_type="user",
        target_id=str(context["user"]["id"]),
        detail={},
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )
    clear_session_cookie(response)
    return {"ok": True}


def _client_ip(request: Request) -> str:
    return client_ip(request)


def _trace_id(request: Request) -> str:
    return trace_id(request)


@router.post(
    "/auth/register",
    status_code=201,
    responses={
        201: {"description": "注册成功，返回账号与访问令牌"},
        403: {"description": "平台已关闭自助注册"},
        409: {"description": "用户名已存在"},
        422: {"description": "用户名/口令/显示名不符合要求"},
    },
)
def register(
    payload: schemas.RegisterPayload, request: Request, repo=Depends(get_repo)
) -> dict[str, Any]:
    user = user_service.register(
        repo,
        username=payload.username,
        display_name=payload.displayName,
        password=payload.password,
        group_name=payload.groupName,
        ip=_client_ip(request),
        trace_id=_trace_id(request),
    )
    return {"user": schemas.user_payload(user), **token_service.issue(repo, user)}


@router.post(
    "/auth/token",
    responses={
        200: {"description": "用户名口令换取 Bearer 令牌"},
        401: {"description": "用户名或口令错误"},
        403: {"description": "账号已停用"},
        429: {"description": "连续失败次数过多，账号锁定中"},
    },
)
def token(payload: schemas.TokenPayload, repo=Depends(get_repo)) -> dict[str, Any]:
    user = token_service.authenticate(repo, payload.username, payload.password)
    return {"user": schemas.user_payload(user), **token_service.issue(repo, user)}


@router.get(
    "/auth/me",
    responses={401: {"description": "未登录、令牌无效或已失效"}},
)
def whoami(context: dict[str, Any] = Depends(require_context)) -> dict[str, Any]:
    return {
        "user": schemas.user_payload(context["user"]),
        "auth": str(context.get("auth") or "cookie"),
    }
