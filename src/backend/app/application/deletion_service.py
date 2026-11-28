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


#: 已抢占（approved）但教案未删：新实现把"抢占 + 删除 + 审计"放进同一事务，
#: 崩溃只会整体回滚为 pending，不再需要"崩溃遗留重试"的补丁路径。


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
    actor_id = int(user["id"])
    # 抢占 + 软删 + 审批审计必须同事务：抢占失败（并发输家）或无权限删时整体回滚，
    # 不会留下"教案已删、申请未决/审计缺失"的状态。
    with repo.transaction():
        if not repo.resolve_deletion_request(request_id, actor_id, status):
            raise AppError("CONFLICT_STALE", "删除申请已处理")
        if approve:
            plan_row = repo.get_plan(plan_id, include_deleted=True)
            if plan_row is None:
                raise AppError("NOT_FOUND", "教案不存在")
            if plan_row.get("deleted_at") is None:
                plan_service.apply_soft_delete(
                    repo, actor_id, plan_id, plan_row, ip=ip, trace_id=trace_id
                )
        audit_service.record(
            repo,
            actor_id=actor_id,
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
