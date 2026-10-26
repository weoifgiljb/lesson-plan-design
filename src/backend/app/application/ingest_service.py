# -*- coding: utf-8 -*-
"""入库编排：先独立复校，再一个写事务里落库；失败与重复都留审计。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.adapters import archive, engine, storage
from app.adapters.db.repo import Repo
from app.application import audit_service
from app.config import MANIFEST_NAME, PLAN_NAME, REPORT_NAME
from app.domain import ingest, manifest as manifest_rules
from app.domain.errors import AppError
from app.domain.verdict import Verdict, fail


@dataclass(frozen=True)
class ImportResult:
    created: bool
    plan_id: int
    version_no: int
    review_id: int
    plan_hash: str


def import_package(
    repo: Repo,
    *,
    files: dict[str, bytes],
    owner_id: int,
    actor_id: int | None = None,
    ip: str = "",
    trace_id: str = "",
) -> ImportResult:
    manifest, plan, report, problem = _load(files)
    if problem is not None:
        return _reject(repo, problem, actor_id, ip, trace_id)
    assert manifest is not None and plan is not None and report is not None
    plan_hash = engine.plan_hash(plan)
    report_sha256 = storage.sha256_bytes(files[REPORT_NAME])
    plan_id, previous_round, duplicate = _prior_state(repo, owner_id, plan, plan_hash, report_sha256)
    verdict = ingest.evaluate(
        manifest=manifest,
        files=files,
        plan=plan,
        report=report,
        report_sha256=report_sha256,
        plan_hash=plan_hash,
        snapshot_hash=_snapshot_hash(report),
        previous_round=_round_floor(previous_round, duplicate, report),
        validation=engine.validate_plan(plan),
    )
    if not verdict.ok:
        return _reject(repo, verdict, actor_id, ip, trace_id)
    if duplicate is not None:
        return _duplicate(repo, duplicate, actor_id, ip, trace_id)
    return _persist(
        repo,
        files=files,
        plan=plan,
        report=report,
        plan_hash=plan_hash,
        report_sha256=report_sha256,
        owner_id=owner_id,
        actor_id=actor_id,
        ip=ip,
        trace_id=trace_id,
        previous_round=previous_round,
    )


def _prior_state(
    repo: Repo, owner_id: int, plan: dict, plan_hash: str, report_sha256: str
) -> tuple[int, int, dict | None]:
    existing_plan = repo.find_plan_by_identity(owner_id, plan)
    if existing_plan is None:
        return 0, 0, None
    plan_id = int(existing_plan["id"])
    return plan_id, repo.last_round(plan_id), repo.find_version(plan_id, plan_hash, report_sha256)


def _round_floor(previous_round: int, duplicate: dict | None, report: dict) -> int:
    """重复包不推进轮次：按包内轮次前一轮校验，其余检查照常执行。"""
    if duplicate is None:
        return previous_round
    round_number = report.get("round")
    return int(round_number) - 1 if isinstance(round_number, int) and round_number > 1 else 0


def _load(files: dict[str, bytes]) -> tuple[dict | None, dict | None, dict | None, Verdict | None]:
    manifest, error = archive.read_json(files, MANIFEST_NAME)
    if error:
        return None, None, None, fail("PAYLOAD_REJECTED", error)
    shape = manifest_rules.check_shape(manifest or {})
    if shape is not None:
        return None, None, None, shape
    plan, error = archive.read_json(files, PLAN_NAME)
    if error:
        return None, None, None, fail("PAYLOAD_REJECTED", error)
    report, error = archive.read_json(files, REPORT_NAME)
    if error:
        return None, None, None, fail("REPORT_INCONSISTENT", error)
    return manifest, plan, report, None


def _snapshot_hash(report: dict[str, Any]) -> str | None:
    snapshot = report.get("planSnapshot")
    return engine.plan_hash(snapshot) if isinstance(snapshot, dict) else None


def _reject(
    repo: Repo, verdict: Verdict, actor_id: int | None, ip: str, trace_id: str
) -> ImportResult:
    audit_service.record(
        repo,
        actor_id=actor_id,
        action="plan.import.rejected",
        target_type="plan",
        target_id="",
        detail={"code": verdict.code, "message": verdict.message, "details": verdict.details},
        ip=ip,
        trace_id=trace_id,
    )
    raise AppError(verdict.code, verdict.message, verdict.details)


def _persist(
    repo: Repo,
    *,
    files: dict[str, bytes],
    plan: dict[str, Any],
    report: dict[str, Any],
    plan_hash: str,
    report_sha256: str,
    owner_id: int,
    actor_id: int | None,
    ip: str,
    trace_id: str,
    previous_round: int,
) -> ImportResult:
    with repo.transaction():
        plan_id = repo.find_or_create_plan(owner_id, plan)
        existing = repo.find_version(plan_id, plan_hash, report_sha256)
        if existing is not None:
            return _duplicate(repo, existing, actor_id, ip, trace_id)
        if repo.last_round(plan_id) != previous_round:
            raise AppError("CONFLICT_STALE", "入库期间出现了新的审查轮次，请重试")
        return _write_version(
            repo,
            plan_id=plan_id,
            files=files,
            plan=plan,
            report=report,
            plan_hash=plan_hash,
            report_sha256=report_sha256,
            actor_id=actor_id,
            ip=ip,
            trace_id=trace_id,
        )


def _write_version(
    repo: Repo,
    *,
    plan_id: int,
    files: dict[str, bytes],
    plan: dict[str, Any],
    report: dict[str, Any],
    plan_hash: str,
    report_sha256: str,
    actor_id: int | None,
    ip: str,
    trace_id: str,
) -> ImportResult:
    version_no = repo.next_version_no(plan_id)
    version_id, created = repo.insert_version_or_existing(
        plan_id,
        version_no,
        json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        plan_hash,
        int(report["schemaVersion"]),
        str(report["rubricVersion"]),
    )
    if not created:
        stored = repo.find_version(plan_id, plan_hash, report_sha256) or {}
        return _duplicate(repo, stored, actor_id, ip, trace_id)
    review_id = repo.insert_review(
        version_id,
        int(report["round"]),
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        report_sha256,
        str(report["status"]),
        str(report.get("independence") or report.get("reviewer") or "role_simulation"),
    )
    repo.insert_findings(review_id, list(report.get("findings") or []))
    repo.insert_overrides(list(report.get("overrides") or []))
    repo.set_current_version(plan_id, version_id)
    storage.store_version_files(plan_id, version_no, files)
    audit_service.record(
        repo,
        actor_id=actor_id,
        action="plan.import",
        target_type="plan",
        target_id=str(plan_id),
        detail={"versionNo": version_no, "reviewId": review_id, "planHash": plan_hash},
        ip=ip,
        trace_id=trace_id,
        after_hash=plan_hash,
    )
    return ImportResult(True, plan_id, version_no, review_id, plan_hash)


def _duplicate(
    repo: Repo, existing: dict[str, Any], actor_id: int | None, ip: str, trace_id: str
) -> ImportResult:
    audit_service.record(
        repo,
        actor_id=actor_id,
        action="plan.import.duplicate",
        target_type="plan",
        target_id=str(existing.get("plan_id") or ""),
        detail={"versionNo": existing.get("version_no")},
        ip=ip,
        trace_id=trace_id,
    )
    return ImportResult(
        False,
        int(existing.get("plan_id") or 0),
        int(existing.get("version_no") or 0),
        int(existing.get("review_id") or 0),
        "",
    )
