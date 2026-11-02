# -*- coding: utf-8 -*-
"""登录编排：锁定、口令校验、会话签发与登录审计。"""
from __future__ import annotations

from typing import Any

from app.adapters import clock
from app.adapters.db.repo import Repo
from app.application import audit_service, session_service
from app.config import LOGIN_LOCK_MINUTES, LOGIN_MAX_FAILURES, allow_registration
from app.domain import auth, roles, security, user_rules
from app.domain.errors import AppError


def register(
    repo: Repo,
    *,
    username: str,
    display_name: str,
    password: str,
    group_name: str = "",
    ip: str = "",
    trace_id: str = "",
) -> dict[str, Any]:
    """自助注册：只开放教师角色，建号即启用，失败原因与建号接口一致。"""
    if not allow_registration():
        raise AppError("REGISTRATION_CLOSED", "平台已关闭自助注册，请联系管理员建号")
    created = create_user(
        repo,
        username=username,
        display_name=display_name,
        role="teacher",
        password=password,
        # 自助注册不允许自选教研组：组成员关系只能由管理员分配，否则可跨组看/下载他人任务
        group_name="",
        actor_id=None,
        ip=ip,
        trace_id=trace_id,
    )
    user = repo.user_by_id(int(created))
    if user is None:
        raise AppError("INTERNAL", "注册后未能读回账号")
    return user


def change_password(
    repo: Repo,
    user: dict[str, Any],
    *,
    old_password: str,
    new_password: str,
    session_id: int | None = None,
    ip: str = "",
    trace_id: str = "",
) -> None:
    """本人改密（BS-05 首次改密）：校验原口令与强度，成功后清除 must_change_password。"""
    if not security.verify_password(old_password, str(user.get("password_hash") or "")):
        audit_service.record(
            repo,
            actor_id=int(user.get("id") or 0),
            action="user.password_failed",
            target_type="user",
            target_id=str(user.get("id") or ""),
            detail={"reason": "old_password_mismatch"},
            ip=ip,
            trace_id=trace_id,
        )
        raise AppError("AUTH_REQUIRED", "原口令不正确")
    problem = security.password_problem(new_password)
    if problem:
        raise AppError("PAYLOAD_REJECTED", problem)
    if new_password == old_password:
        raise AppError("PAYLOAD_REJECTED", "新口令不能与原口令相同")
    with repo.transaction():
        repo.set_password(int(user["id"]), security.hash_password(new_password))
        repo.set_must_change_password(int(user["id"]), False)
        if session_id is not None:
            # 改密后其他设备的会话一律失效，避免口令泄露后旧 Cookie 继续可用（R3-F7）
            repo.revoke_other_sessions(int(user["id"]), int(session_id))
        audit_service.record(
            repo,
            actor_id=int(user.get("id") or 0),
            action="user.password_changed",
            target_type="user",
            target_id=str(user["id"]),
            detail={},
            ip=ip,
            trace_id=trace_id,
        )


def create_user(
    repo: Repo,
    *,
    username: str,
    display_name: str,
    role: str,
    password: str,
    group_name: str = "",
    actor_id: int | None = None,
    ip: str = "",
    trace_id: str = "",
) -> int:
    if not roles.is_valid_role(role):
        raise AppError("PAYLOAD_REJECTED", f"角色非法：{role}")
    problem = security.password_problem(password)
    if problem:
        raise AppError("PAYLOAD_REJECTED", problem)
    data = user_rules.validate(username, display_name, group_name)
    with repo.transaction():
        if repo.user_by_username(data["username"]) is not None:
            raise AppError("CONFLICT_STALE", f"用户名已存在：{data['username']}")
        user_id = repo.insert_user(
            data["username"], data["display_name"], role, security.hash_password(password),
            data["group_name"], must_change_password=True,
        )
        audit_service.record(
            repo,
            actor_id=actor_id,
            action="user.create",
            target_type="user",
            target_id=str(user_id),
            detail={"username": data["username"], "role": role, "group": data["group_name"]},
            ip=ip,
            trace_id=trace_id,
        )
    return user_id


def list_users(
    repo: Repo, *, filters: dict[str, Any], page: int | None, page_size: int | None
) -> dict[str, Any]:
    from app.domain import library  # noqa: PLC0415 - 避免循环导入

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


def verify_credentials(
    repo: Repo, username: str, password: str, *, ip: str = "", trace_id: str = ""
) -> dict[str, Any]:
    """校验账号口令（含锁定/失败计数），成功时不创建会话，供换令牌等无 Cookie 场景使用。"""
    return _authenticate(repo, username, password, ip, trace_id)


def login(
    repo: Repo, username: str, password: str, *, ip: str = "", trace_id: str = ""
) -> tuple[dict[str, Any], str, str]:
    """网页登录：校验口令并创建会话，返回 (user, session_token, csrf_token)。"""
    user = _authenticate(repo, username, password, ip, trace_id)
    token, csrf_token = session_service.create(repo, int(user["id"]))
    _audit(repo, int(user["id"]), "auth.login", {}, ip, trace_id)
    return user, token, csrf_token


def _authenticate(
    repo: Repo, username: str, password: str, ip: str, trace_id: str
) -> dict[str, Any]:
    user = repo.user_by_username(username)
    if user is None:
        _audit(repo, None, "auth.login.failed", {"username": username, "reason": "unknown_user"}, ip, trace_id)
        raise AppError("AUTH_REQUIRED", "用户名或口令错误")
    if not user.get("active"):
        _audit(repo, int(user["id"]), "auth.login.failed", {"reason": "inactive"}, ip, trace_id)
        raise AppError("FORBIDDEN", "账号已停用")
    locked_until = str(user.get("locked_until") or "")
    if locked_until and not clock.is_past(locked_until):
        _audit(repo, int(user["id"]), "auth.login.locked", {}, ip, trace_id)
        raise AppError("RATE_LIMITED", "账号已锁定，请稍后再试")
    if locked_until:
        # 锁定期已过：失败计数必须归零，否则"每 10 分钟错一次"即可永久锁死该账号
        repo.reset_login_failure(int(user["id"]))
        user = {**user, "failed_count": 0, "locked_until": None}
    return _verify(repo, user, password, ip, trace_id)


def _verify(repo: Repo, user: dict[str, Any], password: str, ip: str, trace_id: str) -> dict[str, Any]:
    if not security.verify_password(password, str(user["password_hash"])):
        # 计数走单条原子 UPDATE：并发登录时"读-改-写"会丢更新，锁定可被绕过（R2-1）
        locked_until = clock.iso_after(LOGIN_LOCK_MINUTES / 60)
        count = repo.bump_login_failure(int(user["id"]), LOGIN_MAX_FAILURES, locked_until)
        _audit(repo, int(user["id"]), "auth.login.failed", {"reason": "bad_password", "count": count}, ip, trace_id)
        if count >= LOGIN_MAX_FAILURES:
            raise AppError("RATE_LIMITED", "连续失败次数过多，账号已锁定 10 分钟")
        raise AppError("AUTH_REQUIRED", "用户名或口令错误")
    repo.reset_login_failure(int(user["id"]))
    return user


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
