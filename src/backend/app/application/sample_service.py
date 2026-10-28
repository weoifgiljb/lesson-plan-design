# -*- coding: utf-8 -*-
"""样例库编排：上传校验、重复检测、文件落盘与完整性。"""
from __future__ import annotations

from typing import Any

from app.adapters import archive, engine, storage
from app.adapters.db.repo import Repo
from app.application import audit_service
from app.domain import library, sample_rules
from app.domain.errors import AppError


def create(
    repo: Repo,
    user: dict[str, Any],
    data: bytes,
    *,
    ip: str = "",
    trace_id: str = "",
) -> dict[str, Any]:
    plan, problem = archive.read_json({"plan.json": data}, "plan.json")
    if problem is not None or plan is None:
        raise AppError("PAYLOAD_REJECTED", f"样例 JSON 无效：{problem}")
    sample_rules.require_valid(engine.validate_plan(plan))
    identity = sample_rules.identity(plan)
    plan_hash = engine.plan_hash(plan)
    with repo.transaction():
        if repo.find_sample(identity["course"], identity["week"], identity["session"], identity["title"]):
            raise AppError("CONFLICT_STALE", "同一课题的样例已存在")
        path = storage.write_sample(plan_hash, data)
        sample_id = repo.insert_sample(
            identity["course"], identity["week"], identity["session"], identity["title"], path, plan_hash
        )
        audit_service.record(
            repo,
            actor_id=int(user.get("id") or 0),
            action="sample.create",
            target_type="sample",
            target_id=str(sample_id),
            detail={"planHash": plan_hash, "title": identity["title"], "path": path},
            ip=ip,
            trace_id=trace_id,
        )
    return {
        "sampleId": sample_id,
        **identity,
        "planHash": plan_hash,
        "valid": True,
        "complete": True,
    }


def list_samples(
    repo: Repo,
    *,
    filters: dict[str, Any],
    page: int | None,
    page_size: int | None,
) -> dict[str, Any]:
    actual_page, actual_size, offset = library.page_params(page, page_size)
    rows, total = repo.list_samples(filters, actual_size, offset)
    return {
        "items": [_item(row) for row in rows],
        "page": actual_page,
        "pageSize": actual_size,
        "total": total,
    }


def _item(row: dict[str, Any]) -> dict[str, Any]:
    raw = storage.read_sample(str(row["json_path"]))
    complete = False
    valid = False
    rule_version = ""
    if raw is not None:
        plan, problem = archive.read_json({"plan.json": raw}, "plan.json")
        if problem is None and plan is not None:
            complete = engine.plan_hash(plan) == row["plan_hash"]
            validation = engine.validate_plan(plan)
            valid = validation.get("ok") is True
            rule_version = str(validation.get("ruleVersion") or "")
    return {
        "sampleId": int(row["id"]),
        "course": row["course"],
        "week": int(row["week"]),
        "session": int(row["session"]),
        "title": row["title"],
        "planHash": row["plan_hash"],
        "valid": valid and complete,
        "ruleVersion": rule_version,
        "complete": complete,
    }
