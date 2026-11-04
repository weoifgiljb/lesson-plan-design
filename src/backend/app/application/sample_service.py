# -*- coding: utf-8 -*-
"""样例库编排：上传校验、重复检测、文件落盘与完整性。"""
from __future__ import annotations

from typing import Any

from app.adapters import archive, engine, storage
from app.adapters.db.repo import Repo
from app.application import audit_service
from app.config import files_dir
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
    validation = engine.validate_plan(plan)
    sample_rules.require_valid(validation)
    identity = sample_rules.identity(plan)
    plan_hash = engine.plan_hash(plan)
    score = int(engine.score_plan(plan).get("score") or 0)
    rule_version = str(validation.get("ruleVersion") or "")
    engine_version = engine.engine_version()
    with repo.transaction():
        if repo.find_sample(identity["course"], identity["week"], identity["session"], identity["title"]):
            raise AppError("CONFLICT_STALE", "同一课题的样例已存在")
        path = storage.write_sample(plan_hash, data)
        sample_id = repo.insert_sample(
            identity["course"],
            identity["week"],
            identity["session"],
            identity["title"],
            path,
            plan_hash,
            score=score,
            engine_version=engine_version,
            rule_version=rule_version,
        )
        audit_service.record(
            repo,
            actor_id=int(user.get("id") or 0),
            action="sample.create",
            target_type="sample",
            target_id=str(sample_id),
            detail={
                "planHash": plan_hash,
                "title": identity["title"],
                "path": path,
                "score": score,
                "ruleVersion": rule_version,
            },
            ip=ip,
            trace_id=trace_id,
        )
    return {
        "sampleId": sample_id,
        **identity,
        "planHash": plan_hash,
        "score": score,
        "ruleVersion": rule_version,
        "engineVersion": engine_version,
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
        "items": [_item(repo, row) for row in rows],
        "page": actual_page,
        "pageSize": actual_size,
        "total": total,
    }


def _asset_status(repo: Repo, sample_id: int) -> tuple[bool, list[dict[str, Any]]]:
    """挂接在本样例上的资产：文件在且哈希对才算完整（asset 表此前零引用）。"""
    rows = repo.list_assets(f"sample:{int(sample_id)}")
    statuses: list[dict[str, Any]] = []
    ok = True
    for row in rows:
        target = files_dir() / str(row["path"])
        exists = target.is_file()
        digest = storage.sha256_bytes(target.read_bytes()) if exists else ""
        matched = exists and digest == str(row["sha256"])
        ok = ok and matched
        statuses.append(
            {
                "assetId": int(row["id"]),
                "kind": str(row["kind"]),
                "path": str(row["path"]),
                "sha256": str(row["sha256"]),
                "exists": exists,
                "hashMatched": matched,
                "caption": str(row.get("caption") or ""),
            }
        )
    return ok, statuses


def _item(repo: Repo, row: dict[str, Any]) -> dict[str, Any]:
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
    assets_ok, assets = _asset_status(repo, int(row["id"]))
    complete = complete and assets_ok
    return {
        "sampleId": int(row["id"]),
        "course": row["course"],
        "week": int(row["week"]),
        "session": int(row["session"]),
        "title": row["title"],
        "planHash": row["plan_hash"],
        "score": int(row.get("score") or 0),
        "valid": valid and complete,
        "ruleVersion": str(row.get("rule_version") or rule_version),
        "engineVersion": str(row.get("engine_version") or ""),
        "complete": complete,
        "assetCount": len(assets),
        "assetsOk": assets_ok,
        "assets": assets,
    }


def detail(repo: Repo, sample_id: int) -> dict[str, Any]:
    """样例详情/预览：返回元信息 + 原始教案 JSON。"""
    row = repo.get_sample(int(sample_id))
    if row is None:
        raise AppError("NOT_FOUND", "样例不存在")
    raw = storage.read_sample(str(row["json_path"]))
    plan, problem = archive.read_json({"plan.json": raw or b""}, "plan.json")
    content = plan if problem is None and plan is not None else None
    return {**_item(repo, row), "content": content}


def download(repo: Repo, sample_id: int) -> tuple[dict[str, Any], bytes]:
    """下载原始样例 JSON，插件端可直接使用；被篡改/替换的样例必须拒绝（R3-N1）。"""
    row = repo.get_sample(int(sample_id))
    if row is None:
        raise AppError("NOT_FOUND", "样例不存在")
    raw = storage.read_sample(str(row["json_path"]))
    if raw is None:
        raise AppError("NOT_FOUND", "样例文件缺失")
    plan, problem = archive.read_json({"plan.json": raw}, "plan.json")
    if problem is not None or plan is None:
        raise AppError("HASH_MISMATCH", "样例文件不可解析，拒绝下载")
    if engine.plan_hash(plan) != str(row["plan_hash"]):
        raise AppError("HASH_MISMATCH", "样例文件与登记哈希不一致，拒绝下载")
    return _item(repo, row), raw
