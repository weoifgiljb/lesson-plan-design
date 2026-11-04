# -*- coding: utf-8 -*-
"""同步日志写入：只追加，记录 created/duplicate/conflict/rejected。"""
from __future__ import annotations

from typing import Any

from app.adapters.db.repo import Repo


def record(
    repo: Repo, sync: dict[str, Any], plan_hash: str, result: str, conflict_code: str = ""
) -> None:
    repo.insert_sync_log(
        str(sync.get("direction") or "push"),
        str(sync.get("package_sha256") or ""),
        plan_hash,
        result,
        conflict_code,
        sync.get("operator_id"),
    )
