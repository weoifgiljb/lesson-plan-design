# -*- coding: utf-8 -*-
"""登录编排：锁定、口令校验、会话签发与登录审计。"""
from __future__ import annotations

from typing import Any

from app.adapters import clock
from app.adapters.db.repo import Repo
from app.application import audit_service, session_service
from app.config import LOGIN_LOCK_MINUTES, LOGIN_MAX_FAILURES
from app.domain import auth, roles, security
from app.domain.errors import AppError


def create_user(
    repo: Repo, *, username: str, display_name: str, role: str, password: str,
    group_name: str = "", actor_id: int | None = None, ip: str = "", trace_id: str = "",
) -> int:
    if not roles.is_valid_role(role):
        raise AppError("PAYLOAD_REJECTED", f"角色非法：{role}")
    problem = security.password_problem(password)
    if problem:
        raise AppError("PAYLOAD_REJECTED", problem)
    if repo.user_by_username(username) is not None:
        raise AppError("CONFLICT_STALE", f"用户名已存在：{username}")
    user_id = repo.insert_user(username, display_name, role, security.hash_password(password), group_name)
    audit_service.record(
        repo,
        actor_id=actor_id,
        action="user.create",
        target_type="user",
        target_id=str(user_id),
        detail={"username": username, "role": role, "group": group_name},
        ip=ip,
        trace_id=trace_id,
    )
    return user_id


def list_users(
    repo: Repo, *, filters: dict[str, Any], page: int | None, page_size: int | None
) -> dict[str, Any]:
    from app.domain import library  # noqa: PLC0415 - 避免循环

    actual_page, actual_size, offset = library.page_params(page, page_size)
    rows, total = repo.list_users(filters, actual_size, offset)
    return {
        "items": [
            {
                "userId": int(row["id"]),
                "username": row["username"],
                "displayName": row["display_name"],
                "group": row["group_name"],
                "role": row["role"],
                "active": bool(row["active"]),
                "mustChangePassword": bool(row["must_change_password"]),
                "createdAt": row["created_at"],
            }
            for row in rows
        ],
        "page": actual_page,
        "pageSize": actual_size,
        "total": total,
    }


def login(
    repo: Repo, username: str, password: str, *, ip: str = "", trace_id: str = ""
) -> tuple[dict[str, Any], str, str]:
    user = repo.user_by_username(username)
    if user is None:
        _audit(repo, None, "auth.login.failed", {"username": username, "reason": "unknown_user"}, ip, trace_id)
        raise AppError("AUTH_REQUIRED", "用户名或口令错误")
    if not user.get("active"):
        _audit(repo, int(user["id"]), "auth.login.failed", {"reason": "inactive"}, ip, trace_id)
        raise AppError("FORBIDDEN", "账号已停用")
    if user.get("locked_until") and not clock.is_past(str(user["locked_until"])):
        _audit(repo, int(user["id"]), "auth.login.locked", {}, ip, trace_id)
        raise AppError("RATE_LIMITED", "账号已锁定，请稍后再试")
    if user.get("locked_until"):
        # 锁定已到期：清零失败计数，避免下一次失败立刻再次锁定。
        repo.reset_login_failure(int(user["id"]))
        user = {**user, "failed_count": 0, "locked_until": None}
    return _verify(repo, user, password, ip, trace_id)


def _verify(
    repo: Repo, user: dict[str, Any], password: str, ip: str, trace_id: str
) -> tuple[dict[str, Any], str, str]:
    if not security.verify_password(password, str(user["password_hash"])):
        count, lock = auth.next_failure(int(user["failed_count"]), LOGIN_MAX_FAILURES)
        locked_until = clock.iso_after(LOGIN_LOCK_MINUTES / 60) if lock else None
        repo.record_login_failure(int(user["id"]), count, locked_until)
        _audit(repo, int(user["id"]), "auth.login.failed", {"reason": "bad_password", "count": count}, ip, trace_id)
        if lock:
            raise AppError("RATE_LIMITED", "连续失败次数过多，账号已锁定 10 分钟")
        raise AppError("AUTH_REQUIRED", "用户名或口令错误")
    repo.reset_login_failure(int(user["id"]))
    token, csrf_token = session_service.create(repo, int(user["id"]))
    _audit(repo, int(user["id"]), "auth.login", {}, ip, trace_id)
    return user, token, csrf_token


def _audit(
    repo: Repo, actor_id: int | None, action: str, detail: dict[str, Any], ip: str, trace_id: str
) -> None:
    audit_service.record(
        repo,
        actor_id=actor_id,
        action=action,
        target_type="user",
        target_id=str(actor_id or ""),
        detail=detail,
        ip=ip,
        trace_id=trace_id,
    )
