# -*- coding: utf-8 -*-
"""令牌编排：为用户签发 JWT、校验 Bearer 令牌并按库内 token_version 失效。"""
from __future__ import annotations

from typing import Any

from app.adapters import clock
from app.adapters.db.repo import Repo
from app.config import jwt_secret, jwt_ttl_minutes
from app.domain import security, tokens
from app.domain.errors import AppError

BEARER_PREFIX = "bearer "


def issue(repo: Repo, user: dict[str, Any]) -> dict[str, Any]:
    ttl_seconds = int(jwt_ttl_minutes()) * 60
    expires_at = clock.iso_after(ttl_seconds / 3600)
    token = tokens.issue(
        {
            "sub": int(user["id"]),
            "username": str(user.get("username") or ""),
            "role": str(user.get("role") or ""),
            "tv": int(user.get("token_version") or 1),
            "exp": int(clock.timestamp()) + ttl_seconds,
            "iss": "lpp",
        },
        jwt_secret(),
    )
    return {
        "accessToken": token,
        "tokenType": "Bearer",
        "expiresIn": ttl_seconds,
        "expiresAt": expires_at,
    }


def identity_from_header(repo: Repo, header: str) -> dict[str, Any] | None:
    """解析 `Authorization: Bearer <jwt>`；无该头返回 None，令牌无效抛 401。"""
    value = str(header or "").strip()
    if not value:
        return None
    if not value.lower().startswith(BEARER_PREFIX):
        raise AppError("AUTH_REQUIRED", "Authorization 头格式应为 Bearer <token>")
    raw = value[len(BEARER_PREFIX):].strip()
    claims, problem = tokens.decode(raw, jwt_secret())
    if claims is None:
        raise AppError("AUTH_REQUIRED", f"令牌无效：{problem}")
    user = repo.user_by_id(int(claims.get("sub") or 0))
    if user is None or not user.get("active"):
        raise AppError("AUTH_REQUIRED", "账号不存在或已停用")
    if int(user.get("token_version") or 1) != int(claims.get("tv") or 0):
        # 改密/重置后 token_version 自增，旧令牌一律失效
        raise AppError("AUTH_REQUIRED", "令牌已失效，请重新登录")
    return user


def authenticate(repo: Repo, username: str, password: str) -> dict[str, Any]:
    """账号口令换令牌：与登录共用锁定与失败计数逻辑（见 user_service.login）。"""
    from app.application import user_service

    user, _, _ = user_service.login(repo, username, password)
    return user


def password_problem(password: str) -> str:
    return security.password_problem(password)
