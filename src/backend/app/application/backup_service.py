# -*- coding: utf-8 -*-
"""OPS-08 管理端备份编排：调用文件适配层并写审计。"""
from __future__ import annotations

from typing import Any

from app.adapters import backup_store
from app.adapters.db.repo import Repo
from app.application import audit_service


def list_snapshots() -> dict[str, Any]:
    return backup_store.list_snapshots()


def create(repo: Repo, user: dict[str, Any], label: str, *, ip: str = "", trace_id: str = "") -> dict[str, Any]:
    result = backup_store.create(label)
    audit_service.record(
        repo,
        actor_id=int(user["id"]),
        action="backup.create",
        target_type="backup",
        target_id=str(result["path"]),
        detail={"label": label.strip() or "manual"},
        ip=ip,
        trace_id=trace_id,
    )
    return result


def archive(name: str) -> tuple[Any, str]:
    return backup_store.archive(name)


def restore(repo: Repo, user: dict[str, Any], name: str, *, ip: str = "", trace_id: str = "") -> dict[str, Any]:
    result = backup_store.restore(name)
    audit_service.record(
        repo,
        actor_id=int(user["id"]),
        action="backup.restore",
        target_type="backup",
        target_id=name,
        detail={
            "target": result["target"],
            "preRestore": result["preRestore"].split("/")[-1].split("\\")[-1],
            "rows": result["rows"],
            "schemaVersion": result["schemaVersion"],
        },
        ip=ip,
        trace_id=trace_id,
    )
    return {"ok": True, **result}
