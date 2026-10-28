# -*- coding: utf-8 -*-
"""导出中心编排：门禁 → 插件导出 → 落盘哈希 → 复用与审计。"""
from __future__ import annotations

import json
from typing import Any

from app.adapters import engine, storage
from app.adapters.db.repo import Repo
from app.application import audit_service
from app.domain import export_rules, library
from app.domain.errors import AppError

MAX_BATCH = 50


def create(
    repo: Repo,
    user: dict[str, Any],
    version_ids: list[int],
    *,
    ip: str = "",
    trace_id: str = "",
) -> dict[str, Any]:
    ids = _validate_ids(version_ids)
    items: list[dict[str, Any]] = []
    created = 0
    reused = 0
    for version_id in ids:
        item, was_created, was_reused = _export_one(repo, user, version_id, ip, trace_id)
        items.append(item)
        created += 1 if was_created else 0
        reused += 1 if was_reused else 0
    return {"items": items, "created": created, "reused": reused}


def detail(repo: Repo, user: dict[str, Any], export_id: int) -> dict[str, Any]:
    row = _visible_job(repo, user, export_id)
    return _job_payload(row)


def download(repo: Repo, user: dict[str, Any], export_id: int) -> tuple[dict[str, Any], bytes]:
    row = _visible_job(repo, user, export_id)
    if row.get("status") != "succeeded" or not row.get("docx_path"):
        raise AppError("NOT_FOUND", "导出产物不存在")
    path = storage.export_path(int(export_id))
    if not path.exists():
        raise AppError("NOT_FOUND", "导出产物文件缺失")
    return _job_payload(row), path.read_bytes()


def _export_one(
    repo: Repo, user: dict[str, Any], version_id: int, ip: str, trace_id: str
) -> tuple[dict[str, Any], bool, bool]:
    row = repo.version_by_id(version_id)
    if row is None or row.get("deleted_at") is not None:
        return _failed(version_id, "NOT_FOUND", "教案版本不存在"), False, False
    if not _visible(row, user):
        audit_service.record(
            repo, actor_id=int(user.get("id") or 0), action="plan.export.failed",
            target_type="plan_version", target_id=str(version_id),
            detail={"code": "FORBIDDEN"}, ip=ip, trace_id=trace_id,
        )
        return _failed(version_id, "FORBIDDEN", "无权导出该版本"), False, False
    plan = json.loads(row["content_json"])
    report = json.loads(row["report_json"]) if row.get("report_json") else {}
    problem = _gate_problem(row, plan, report)
    if problem is not None:
        return problem, False, False
    engine_version = engine.engine_version()
    existing = repo.find_export_job(version_id, engine_version)
    if existing is not None:
        existing = repo.get_export_job(int(existing["id"]))
    if existing is not None and existing.get("docx_path") and storage.export_path(int(existing["id"])).exists():
        return _job_payload(existing), False, True
    return _perform_export(repo, user, row, plan, engine_version, ip, trace_id)


def _gate_problem(row: dict[str, Any], plan: dict[str, Any], report: dict[str, Any]) -> dict[str, Any] | None:
    status = row.get("review_status")
    if status not in export_rules.ALLOWED_REPORT_STATUS:
        return _failed(int(row["version_id"]), "REPORT_INCONSISTENT", f"审查状态不允许导出：{status}")
    verdict = export_rules.gate(engine.validate_plan(plan), report)
    if verdict.ok:
        return None
    return _failed(int(row["version_id"]), verdict.code, verdict.message)


def _perform_export(
    repo: Repo, user: dict[str, Any], row: dict[str, Any], plan: dict[str, Any],
    engine_version: str, ip: str, trace_id: str,
) -> tuple[dict[str, Any], bool, bool]:
    version_id = int(row["version_id"])
    job_id = repo.create_export_job(version_id, engine_version, int(user.get("id") or 0), "pending")
    result = engine.export_docx(plan, storage.export_path(job_id))
    if not result.get("ok"):
        repo.update_export_job(job_id, "failed")
        _audit_failure(repo, user, version_id, result.get("message", "导出失败"), ip, trace_id)
        return _failed(version_id, result.get("code", "INTERNAL"), result.get("message", "导出失败")), False, False
    warnings = result["result"].get("warnings") or []
    if warnings:
        storage.export_path(job_id).unlink(missing_ok=True)
        repo.update_export_job(job_id, "failed")
        message = "；".join(warnings)
        _audit_failure(repo, user, version_id, message, ip, trace_id)
        return _failed(version_id, "MEDIA_MISSING", message), False, False
    data = storage.export_path(job_id).read_bytes()
    digest = storage.sha256_bytes(data)
    repo.update_export_job(job_id, "succeeded", f"exports/{job_id}.docx", digest)
    audit_service.record(
        repo, actor_id=int(user.get("id") or 0), action="plan.export",
        target_type="plan_version", target_id=str(version_id),
        detail={"exportId": job_id, "docxSha256": digest, "engineVersion": engine_version},
        ip=ip, trace_id=trace_id, after_hash=digest,
    )
    return {
        "planVersionId": version_id,
        "exportId": job_id,
        "status": "succeeded",
        "engineVersion": engine_version,
        "docxSha256": digest,
        "planHash": row["plan_hash"],
    }, True, False


def _validate_ids(version_ids: list[int]) -> list[int]:
    if not isinstance(version_ids, list) or not version_ids:
        raise AppError("PAYLOAD_REJECTED", "planVersionIds 不能为空")
    unique: list[int] = []
    for value in version_ids:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise AppError("PAYLOAD_REJECTED", "planVersionIds 必须是正整数")
        if value not in unique:
            unique.append(value)
    if len(unique) > MAX_BATCH:
        raise AppError("PAYLOAD_REJECTED", f"单次最多导出 {MAX_BATCH} 份")
    return unique


def _visible_job(repo: Repo, user: dict[str, Any], export_id: int) -> dict[str, Any]:
    row = repo.get_export_job(export_id)
    if row is None:
        raise AppError("NOT_FOUND", "导出记录不存在")
    if not _visible(row, user):
        raise AppError("FORBIDDEN", "无权访问该导出记录")
    return row


def _visible(row: dict[str, Any], user: dict[str, Any]) -> bool:
    return library.can_view(
        str(user.get("role") or ""),
        int(user.get("id") or 0),
        str(user.get("group_name") or ""),
        int(row["owner_id"]),
        str(row.get("owner_group") or ""),
    )


def _job_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "exportId": int(row["id"]),
        "planVersionId": int(row["plan_version_id"]),
        "planId": int(row["plan_id"]),
        "versionNo": int(row["version_no"]),
        "contentTitle": row["content_title"],
        "status": row["status"],
        "engineVersion": row["engine_version"],
        "docxSha256": row["docx_sha256"],
        "createdAt": row["created_at"],
    }


def _failed(version_id: int, code: str, message: str) -> dict[str, Any]:
    return {"planVersionId": version_id, "status": "failed", "code": code, "message": message}


def _audit_failure(
    repo: Repo, user: dict[str, Any], version_id: int, message: str, ip: str, trace_id: str
) -> None:
    audit_service.record(
        repo, actor_id=int(user.get("id") or 0), action="plan.export.failed",
        target_type="plan_version", target_id=str(version_id),
        detail={"message": message}, ip=ip, trace_id=trace_id,
    )
