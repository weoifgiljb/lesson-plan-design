# -*- coding: utf-8 -*-
"""教案库编排：可见范围、详情、版本链、差异与软删除。"""
from __future__ import annotations

import json
from typing import Any

from app.adapters.db.repo import Repo
from app.application import audit_service
from app.domain import diff, library
from app.domain.errors import AppError


def list_plans(
    repo: Repo,
    user: dict[str, Any],
    *,
    filters: dict[str, Any],
    page: int | None,
    page_size: int | None,
) -> dict[str, Any]:
    actual_page, actual_size, offset = library.page_params(page, page_size)
    rows, total = repo.list_plans(library.scope_for(user), filters, actual_size, offset)
    return {
        "items": [_item(row) for row in rows],
        "page": actual_page,
        "pageSize": actual_size,
        "total": total,
    }


def plan_detail(repo: Repo, user: dict[str, Any], plan_id: int) -> dict[str, Any]:
    row = _visible(repo, user, plan_id)
    versions = repo.list_versions(plan_id)
    current = next((item for item in versions if item["version_no"] == row["version_no"]), None)
    payload = {
        "plan": _item(row),
        "currentVersion": None,
        "latestReview": None,
    }
    if current is not None:
        payload["currentVersion"] = {
            "versionNo": current["version_no"],
            "planHash": current["plan_hash"],
            "engineVersion": current["engine_version"],
            "createdAt": current["created_at"],
            "content": json.loads(current["content_json"]),
        }
        payload["latestReview"] = _review_payload(current)
    return payload


def plan_versions(repo: Repo, user: dict[str, Any], plan_id: int) -> dict[str, Any]:
    _visible(repo, user, plan_id)
    items = [
        {
            "versionNo": row["version_no"],
            "planHash": row["plan_hash"],
            "engineVersion": row["engine_version"],
            "createdAt": row["created_at"],
            **_review_fields(row),
        }
        for row in repo.list_versions(plan_id)
    ]
    return {"planId": plan_id, "items": items, "total": len(items)}


def plan_diff(
    repo: Repo,
    user: dict[str, Any],
    plan_id: int,
    *,
    from_version: int | None = None,
    to_version: int | None = None,
) -> dict[str, Any]:
    _visible(repo, user, plan_id)
    versions = repo.list_versions(plan_id)
    numbers = [int(item["version_no"]) for item in versions]
    if len(numbers) < 2:
        raise AppError("NOT_FOUND", "至少需要两个版本才能对比")
    source_no = int(from_version or numbers[-2])
    target_no = int(to_version or numbers[-1])
    if source_no == target_no or source_no not in numbers or target_no not in numbers:
        raise AppError("NOT_FOUND", f"版本不存在：{source_no} -> {target_no}")
    source = repo.version_by_no(plan_id, source_no)
    target = repo.version_by_no(plan_id, target_no)
    if source is None or target is None:
        raise AppError("NOT_FOUND", "版本不存在")
    changes = diff.diff_plans(json.loads(source["content_json"]), json.loads(target["content_json"]))
    return {
        "planId": plan_id,
        "fromVersion": source_no,
        "toVersion": target_no,
        "changes": changes,
        "count": len(changes),
    }


def delete_plan(
    repo: Repo, user: dict[str, Any], plan_id: int, *, ip: str = "", trace_id: str = ""
) -> dict[str, Any]:
    row = repo.get_plan(plan_id, include_deleted=True)
    if row is None:
        raise AppError("NOT_FOUND", "教案不存在")
    actor_id = int(user.get("id") or 0)
    if not library.can_delete(str(user.get("role") or ""), actor_id, int(row["owner_id"])):
        _audit_denied(repo, user, plan_id, "plan.delete", ip, trace_id)
        raise AppError("FORBIDDEN", "只能删除本人教案")
    already = row.get("deleted_at") is not None
    if not already:
        repo.soft_delete_plan(plan_id)
    audit_service.record(
        repo,
        actor_id=actor_id,
        action="plan.delete",
        target_type="plan",
        target_id=str(plan_id),
        detail={"alreadyDeleted": already},
        ip=ip,
        trace_id=trace_id,
        before_hash=str(row.get("plan_hash") or ""),
    )
    return {"planId": plan_id, "deleted": True, "alreadyDeleted": already}


def _visible(repo: Repo, user: dict[str, Any], plan_id: int) -> dict[str, Any]:
    row = repo.get_plan(plan_id)
    if row is None:
        raise AppError("NOT_FOUND", "教案不存在")
    allowed = library.can_view(
        str(user.get("role") or ""),
        int(user.get("id") or 0),
        str(user.get("group_name") or ""),
        int(row["owner_id"]),
        str(row["owner_group"] or ""),
    )
    if not allowed:
        _audit_denied(repo, user, plan_id, "plan.read", "", "")
        raise AppError("FORBIDDEN", "无权访问该教案")
    return row


def _audit_denied(
    repo: Repo, user: dict[str, Any], plan_id: int, action: str, ip: str, trace_id: str
) -> None:
    audit_service.record(
        repo,
        actor_id=int(user.get("id") or 0),
        action=f"{action}.denied",
        target_type="plan",
        target_id=str(plan_id),
        detail={"role": user.get("role")},
        ip=ip,
        trace_id=trace_id,
    )


def _item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "planId": int(row["plan_id"]),
        "contentTitle": row["content_title"],
        "course": row["course"],
        "week": int(row["week"]),
        "session": int(row["session"]),
        "ownerId": int(row["owner_id"]),
        "teacher": row["teacher"],
        "versionNo": row["version_no"],
        "planHash": row["plan_hash"],
        "reviewStatus": row["review_status"],
        "reviewRound": row["review_round"],
        "versionCreatedAt": row["version_created_at"],
    }


def _review_payload(row: dict[str, Any]) -> dict[str, Any] | None:
    if row.get("round") is None:
        return None
    return {
        "round": int(row["round"]),
        "status": row["status"],
        "reviewerMode": row["reviewer_mode"] if "reviewer_mode" in row else None,
        "reportSha256": row["report_sha256"],
    }


def _review_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {"round": row["round"], "status": row["status"], "reportSha256": row["report_sha256"]}
