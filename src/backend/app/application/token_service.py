# -*- coding: utf-8 -*-
"""令牌编排：为用户签发 JWT、校验 Bearer 令牌并按库内 token_version 失效。"""
from __future__ import annotations

from typing import Any

from app.adapters import clock
from app.adapters.db.repo import Repo
from app.config import jwt_secret, jwt_ttl_minutes
from app.application import user_service
from app.domain import tokens
from app.domain.errors import AppError

BEARER_PREFIX = "bearer "


def issue(repo: Repo, user: dict[str, Any]) -> dict[str, Any]:
    ttl_seconds = int(jwt_ttl_minutes()) * 60
    expires_at_ts = int(clock.timestamp()) + ttl_seconds
    token = tokens.issue(
        {
            "sub": int(user["id"]),
            "username": str(user.get("username") or ""),
            "role": str(user.get("role") or ""),
            "tv": int(user.get("token_version") or 1),
            "exp": expires_at_ts,
            "iss": "lpp",
        },
        jwt_secret(),
    )
    return {
        "accessToken": token,
        "tokenType": "Bearer",
        "expiresIn": ttl_seconds,
        "expiresAt": clock.iso_after(ttl_seconds / 3600),
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


def verify_credentials(
    repo: Repo, username: str, password: str, *, ip: str = "", trace_id: str = ""
) -> dict[str, Any]:
    """只校验账号口令（含锁定与失败计数），**不创建会话**——换令牌不该留下 Cookie 会话。"""
    return user_service.verify_credentials(repo, username, password, ip=ip, trace_id=trace_id)
