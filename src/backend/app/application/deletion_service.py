# -*- coding: utf-8 -*-
"""BS-11 教案删除申请：7 个工作日处理，批准后软删除并留审计。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.adapters.db.repo import Repo
from app.application import audit_service, plan_service
from app.domain.errors import AppError


def _business_due(days: int = 7) -> str:
    current = datetime.now(timezone.utc)
    remaining = days
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current.isoformat(timespec="seconds")


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestId": int(row["id"]),
        "planId": int(row["plan_id"]),
        "contentTitle": row.get("content_title") or "",
        "requester": row.get("requester") or "",
        "reason": row.get("reason") or "",
        "status": row.get("status") or "pending",
        "createdAt": row.get("created_at"),
        "dueAt": row.get("due_at"),
        "resolvedAt": row.get("resolved_at"),
        "planDeleted": row.get("deleted_at") is not None,
    }


def request_deletion(
    repo: Repo,
    user: dict[str, Any],
    plan_id: int,
    reason: str,
    *,
    ip: str = "",
    trace_id: str = "",
) -> dict[str, Any]:
    plan = repo.get_plan(plan_id)
    if plan is None:
        raise AppError("NOT_FOUND", "教案不存在")
    if str(user.get("role")) not in {"teacher", "lead"} or int(user.get("id") or 0) != int(plan["owner_id"]):
        raise AppError("FORBIDDEN", "只能为本人教案提交删除申请")
    pending = next(
        (item for item in repo.list_deletion_requests("pending") if int(item["plan_id"]) == plan_id),
        None,
    )
    if pending is not None:
        return _payload(pending)
    request_id = repo.create_deletion_request(plan_id, int(user["id"]), reason.strip(), _business_due())
    audit_service.record(
        repo,
        actor_id=int(user["id"]),
        action="plan.delete.requested",
        target_type="plan",
        target_id=str(plan_id),
        detail={"requestId": request_id, "reason": reason.strip()[:200]},
        ip=ip,
        trace_id=trace_id,
    )
    row = repo.get_deletion_request(request_id)
    if row is None:
        raise AppError("INTERNAL", "删除申请创建失败")
    return _payload(row)


def list_requests(repo: Repo, user: dict[str, Any], status: str | None = None) -> dict[str, Any]:
    if str(user.get("role")) != "admin":
        raise AppError("FORBIDDEN", "只有管理员可以处理删除申请")
    items = [_payload(row) for row in repo.list_deletion_requests(status)]
    return {"items": items, "total": len(items)}


def _claim_request(repo: Repo, request_id: int, resolver_id: int, status: str) -> None:
    if not repo.resolve_deletion_request(request_id, resolver_id, status):
        raise AppError("CONFLICT_STALE", "删除申请已被处理")


def _delete_plan_with_rollback(
    repo: Repo,
    user: dict[str, Any],
    request_id: int,
    plan_id: int,
    *,
    ip: str = "",
    trace_id: str = "",
) -> None:
    """删除失败时把已抢占的申请放回 pending，让管理员可重试；异常继续上抛（不吞错）。"""
    deleted = False
    try:
        plan_service.delete_plan(repo, user, plan_id, ip=ip, trace_id=trace_id)
        deleted = True
    finally:
        if not deleted:
            repo.revert_deletion_request(request_id)


def resolve_request(
    repo: Repo,
    user: dict[str, Any],
    request_id: int,
    approve: bool,
    *,
    ip: str = "",
    trace_id: str = "",
) -> dict[str, Any]:
    if str(user.get("role")) != "admin":
        raise AppError("FORBIDDEN", "只有管理员可以处理删除申请")
    row = repo.get_deletion_request(request_id)
    if row is None:
        raise AppError("NOT_FOUND", "删除申请不存在")
    if row.get("status") != "pending":
        raise AppError("CONFLICT_STALE", "删除申请已处理")
    plan_id = int(row["plan_id"])
    status = "approved" if approve else "rejected"
    # 先原子抢占申请，再删教案：并发审批只允许一个赢家，避免双方都执行删除/重复审计。
    # （delete_plan 自带事务，不能和抢占合并进一个事务——repo.transaction 不支持嵌套。）
    _claim_request(repo, request_id, int(user["id"]), status)
    if approve:
        _delete_plan_with_rollback(repo, user, request_id, plan_id, ip=ip, trace_id=trace_id)
    audit_service.record(
        repo,
        actor_id=int(user["id"]),
        action="plan.delete.approved" if approve else "plan.delete.rejected",
        target_type="plan",
        target_id=str(plan_id),
        detail={"requestId": request_id},
        ip=ip,
        trace_id=trace_id,
    )
    updated = repo.get_deletion_request(request_id)
    if updated is None:
        raise AppError("INTERNAL", "删除申请状态读取失败")
    return _payload(updated)
