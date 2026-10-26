# -*- coding: utf-8 -*-
"""审计编排：把业务动作写入只追加的 audit_log。"""
from __future__ import annotations

from typing import Any

from app.adapters.db.repo import Repo


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
