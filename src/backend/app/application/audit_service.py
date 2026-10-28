# -*- coding: utf-8 -*-
"""审计编排：写入只追加的 audit_log，以及管理员/组长的查询。"""
from __future__ import annotations

import json
from typing import Any

from app.adapters.db.repo import Repo
from app.domain import library, timerange


def record(
    repo: Repo,
    *,
    actor_id: int | None,
    action: str,
    target_type: str,
    target_id: str,
    detail: dict[str, Any] | None = None,
    ip: str = "",
    trace_id: str = "",
    before_hash: str = "",
    after_hash: str = "",
) -> None:
    repo.insert_audit(
        actor_id,
        action,
        target_type,
        target_id,
        detail=detail,
        ip=ip,
        trace_id=trace_id,
        before_hash=before_hash,
        after_hash=after_hash,
    )


def query(
    repo: Repo,
    user: dict[str, Any],
    *,
    filters: dict[str, Any],
    page: int | None,
    page_size: int | None,
) -> dict[str, Any]:
    actual_page, actual_size, offset = library.page_params(page, page_size)
    window = dict(filters)
    window["created_from"] = timerange.start_of(filters["date_from"]) if filters.get("date_from") else None
    window["created_before"] = timerange.end_exclusive(filters["date_to"]) if filters.get("date_to") else None
    rows, total = repo.list_audit_entries(library.scope_for(user), window, actual_size, offset)
    return {
        "items": [_entry(row) for row in rows],
        "page": actual_page,
        "pageSize": actual_size,
        "total": total,
    }


def _entry(row: dict[str, Any]) -> dict[str, Any]:
    actor_id = row["actor_id"]
    return {
        "id": int(row["id"]),
        "actor": {
            "id": int(actor_id) if actor_id is not None else None,
            "name": row["actor_name"] or "系统",
            "role": row["actor_role"] or "",
            "group": row["actor_group"] or "",
        },
        "action": row["action"],
        "targetType": row["target_type"],
        "targetId": row["target_id"],
        "detail": json.loads(row["detail_json"]),
        "ip": row["ip"],
        "traceId": row["trace_id"],
        "beforeHash": row["before_hash"],
        "afterHash": row["after_hash"],
        "createdAt": row["created_at"],
    }
