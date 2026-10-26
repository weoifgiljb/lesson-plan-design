# -*- coding: utf-8 -*-
"""登录、退出：登录公开，退出要求会话 + CSRF。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from app.api import schemas
from app.api.deps import clear_session_cookie, get_repo, require_csrf, set_session_cookie
from app.application import session_service, user_service

router = APIRouter()


@router.post("/auth/login")
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
    return {"user": schemas.user_payload(user), "csrfToken": csrf_token}


@router.post("/auth/logout")
def logout(
    response: Response, context: dict[str, Any] = Depends(require_csrf)
) -> dict[str, Any]:
    session_service.revoke(context["repo"], int(context["session"]["id"]))
    clear_session_cookie(response)
    return {"ok": True}


def _client_ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))
