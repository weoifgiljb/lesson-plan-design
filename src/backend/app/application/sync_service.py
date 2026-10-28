# -*- coding: utf-8 -*-
"""双端同步：头版本、增量拉取、带 baseHash 的推送与冲突。"""
from __future__ import annotations

import json
from typing import Any

from app.adapters import engine, storage
from app.adapters.db.repo import Repo
from app.application import audit_service, ingest_service
from app.domain import diff, library
from app.domain.errors import AppError

PULL_LIMIT_MAX = 100


def head(
    repo: Repo,
    user: dict[str, Any],
    *,
    plan_id: int | None = None,
    identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = _plan_for(repo, user, plan_id, identity)
    if row is None:
        return {"exists": False, "planId": None, "headVersion": None, "headHash": None}
    resolved = int(row["plan_id"]) if "plan_id" in row else int(row["id"])
    return _head_payload(repo, resolved)


def pull(
    repo: Repo, user: dict[str, Any], *, since: int = 0, limit: int = 50
) -> dict[str, Any]:
    actual_limit = min(max(int(limit), 1), PULL_LIMIT_MAX)
    rows = repo.pull_versions(library.scope_for(user), max(int(since), 0), actual_limit + 1)
    has_more = len(rows) > actual_limit
    items = [_pull_item(row) for row in rows[:actual_limit]]
    next_cursor = items[-1]["versionId"] if items else max(int(since), 0)
    return {"items": items, "nextCursor": next_cursor, "hasMore": has_more}


def push(
    repo: Repo,
    user: dict[str, Any],
    *,
    files: dict[str, bytes],
    package_bytes: bytes,
    base_hash: str,
    ip: str = "",
    trace_id: str = "",
) -> dict[str, Any]:
    actor_id = int(user.get("id") or 0)
    package_sha256 = storage.sha256_bytes(package_bytes)
    sync = {
        "direction": "push",
        "package_sha256": package_sha256,
        "operator_id": actor_id,
    }

    def guard(plan: dict[str, Any], report: dict[str, Any]) -> None:
        _check_base_hash(repo, actor_id, plan, base_hash, package_sha256, ip, trace_id)

    result = ingest_service.import_package(
        repo,
        files=files,
        owner_id=actor_id,
        actor_id=actor_id,
        ip=ip,
        trace_id=trace_id,
        sync=sync,
        guard=guard,
    )
    head_payload = _head_payload(repo, result.plan_id)
    return {
        "planId": result.plan_id,
        "versionNo": result.version_no,
        "reviewId": result.review_id,
        "planHash": result.plan_hash,
        "duplicate": not result.created,
        "headVersion": head_payload["headVersion"],
        "headHash": head_payload["headHash"],
    }


def _check_base_hash(
    repo: Repo, actor_id: int, plan: dict[str, Any], base_hash: str,
    package_sha256: str, ip: str, trace_id: str,
) -> None:
    existing = repo.find_plan_by_identity(actor_id, plan)
    if existing is None:
        return
    head = repo.plan_head(int(existing["id"]))
    expected = str(head["plan_hash"]) if head is not None else ""
    if base_hash and base_hash == expected:
        return
    new_hash = engine.plan_hash(plan)
    board = repo.version_by_no(int(existing["id"]), int(head["version_no"])) if head else None
    changes = []
    if board is not None:
        changes = diff.summarize(diff.diff_plans(json.loads(board["content_json"]), plan))
    _audit_conflict(repo, actor_id, existing, expected, base_hash, changes, package_sha256, ip, trace_id)
    raise AppError(
        "CONFLICT_STALE",
        "服务端头版本已变化，请先拉取或改用本地为准上传新版本",
        {
            "headVersion": int(head["version_no"]) if head else 0,
            "headHash": expected,
            "baseHash": base_hash,
            "planHash": new_hash,
            "changes": changes,
        },
    )


def _audit_conflict(
    repo: Repo, actor_id: int, plan_row: dict[str, Any], head_hash: str,
    base_hash: str, changes: list[str], package_sha256: str, ip: str, trace_id: str,
) -> None:
    repo.insert_sync_log(
        "push",
        package_sha256,
        head_hash,
        "conflict",
        "CONFLICT_STALE",
        actor_id,
    )
    audit_service.record(
        repo,
        actor_id=actor_id,
        action="sync.push.conflict",
        target_type="plan",
        target_id=str(plan_row["id"]),
        detail={"headHash": head_hash, "baseHash": base_hash, "changes": changes},
        ip=ip,
        trace_id=trace_id,
    )


def _plan_for(
    repo: Repo, user: dict[str, Any], plan_id: int | None, identity: dict[str, Any] | None
) -> dict[str, Any] | None:
    if plan_id is not None:
        row = repo.get_plan(int(plan_id), include_deleted=True)
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
            raise AppError("FORBIDDEN", "无权访问该教案")
        return row
    data = identity or {}
    if not data.get("contentTitle") or not data.get("week") or not data.get("session"):
        raise AppError("NOT_FOUND", "请提供 planId 或课程周次课次课题")
    return repo.find_plan_by_identity_scope(library.scope_for(user), data)


def _head_payload(repo: Repo, plan_id: int) -> dict[str, Any]:
    head = repo.plan_head(plan_id)
    if head is None:
        return {"exists": False, "planId": plan_id, "headVersion": None, "headHash": None}
    return {
        "exists": True,
        "planId": plan_id,
        "headVersion": int(head["version_no"]),
        "headHash": str(head["plan_hash"]),
        "headVersionId": int(head["version_id"]),
        "updatedAt": head["created_at"],
    }


def _pull_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "versionId": int(row["version_id"]),
        "planId": int(row["plan_id"]),
        "versionNo": int(row["version_no"]),
        "planHash": row["plan_hash"],
        "contentTitle": row["content_title"],
        "teacher": row["teacher"],
        "updatedAt": row["created_at"],
        "deleted": row.get("deleted_at") is not None,
        "content": json.loads(row["content_json"]),
    }
