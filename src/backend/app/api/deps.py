# -*- coding: utf-8 -*-
"""会话、CSRF 与角色依赖；全后端唯一设置 Cookie 的地方。"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, Request, Response

from app.application import audit_service, session_service
from app.api.request_info import client_ip, trace_id
from app.config import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, cookie_secure, session_ttl_hours
from app.domain import auth, roles
from app.domain.errors import AppError


def get_repo(request: Request):
    """每请求独立连接：写事务由 db_lock 串行化，读请求不再与写事务共用连接（P19-3）。"""
    factory = getattr(request.app.state, "repo_factory", None)
    if factory is None:
        raise AppError("INTERNAL", "数据库不可用")
    repo = factory()
    try:
        yield repo
    finally:
        repo.close()


def current_context(request: Request, repo=Depends(get_repo)) -> dict[str, Any]:
    token = request.cookies.get(SESSION_COOKIE, "")
    resolved = session_service.resolve(repo, token)
    if resolved is None:
        raise AppError("AUTH_REQUIRED", "未登录或会话已失效")
    session, user = resolved
    return {"session": session, "user": user, "repo": repo}


def require_role(*allowed_roles: str) -> Callable[..., dict[str, Any]]:
    def dependency(
        request: Request, context: dict[str, Any] = Depends(current_context)
    ) -> dict[str, Any]:
        role = str(context["user"].get("role") or "")
        if not roles.allowed(role, allowed_roles):
            _audit_denied(request, context, "role_denied", {"role": role, "allowed": list(allowed_roles)})
            raise AppError("FORBIDDEN", "无权限执行该操作")
        return context

    return dependency


def require_csrf(
    request: Request, context: dict[str, Any] = Depends(current_context)
) -> dict[str, Any]:
    provided = request.headers.get(CSRF_HEADER, "")
    expected = str(context["session"].get("csrf_token") or "")
    if not auth.csrf_matches(expected, provided):
        _audit_denied(request, context, "csrf_failed")
        raise AppError("FORBIDDEN", "CSRF 校验失败")
    return context


def _audit_denied(
    request: Request, context: dict[str, Any], reason: str, extra: dict[str, Any] | None = None
) -> None:
    """越权与 CSRF 失败留痕（TC-09-01 / AC-06）。未登录的 401 不写，避免放大。"""
    repo = context.get("repo")
    if repo is None:
        return
    user = context.get("user") or {}
    actor_id = int(user["id"]) if user.get("id") else None
    audit_service.record(
        repo,
        actor_id=actor_id,
        action="authz.denied",
        target_type="route",
        target_id=str(request.url.path),
        detail={"reason": reason, **(extra or {})},
        ip=client_ip(request),
        trace_id=trace_id(request),
    )


def set_session_cookie(response: Response, token: str, csrf_token: str) -> None:
    max_age = session_ttl_hours() * 3600
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=cookie_secure(),
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=max_age,
        httponly=False,
        samesite="lax",
        secure=cookie_secure(),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
