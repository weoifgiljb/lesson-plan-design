# -*- coding: utf-8 -*-
"""入库编排：先独立复校，再一个写事务里落库；失败与重复都留审计。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from app.adapters import archive, engine, storage
from app.adapters.db.repo import Repo
from app.application import audit_service, sync_log
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
    sync: dict[str, Any] | None = None,
    guard: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
) -> ImportResult:
    manifest, plan, report, problem = load_package(files)
    if problem is not None:
        return _reject(repo, problem, actor_id, ip, trace_id, sync=sync)
    if manifest is None or plan is None or report is None:
        raise AppError("INTERNAL", "契约包解析结果不完整")
    validation = engine.validate_plan(plan)
    structure = _structure_verdict(validation)
    if structure is not None:
        # 结构未通过时不做任何身份/版本计算，避免未校验字段（如 week 为数组）打穿成 500。
        return _reject(repo, structure, actor_id, ip, trace_id, sync=sync)
    plan_hash = engine.plan_hash(plan)
    report_sha256 = storage.sha256_bytes(files[REPORT_NAME])
    plan_id, previous_round, duplicate = _prior_state(repo, owner_id, plan, plan_hash, report_sha256)
    if duplicate is None and guard is not None:
        # 乐观锁预检：旧客户端推的是旧轮次包，必须先给"头版本已变"的 409 + 差异，
        # 否则会被下面的轮次校验抢先判成 422（TC-08-01 真实场景）。
        # 事务内仍会复检一次，防并发。
        guard(plan, report)
    verdict = _evaluate(
        manifest, files, plan, report, plan_hash, report_sha256, validation, previous_round, duplicate
    )
    if not verdict.ok:
        return _reject(repo, verdict, actor_id, ip, trace_id, sync=sync)
    if duplicate is not None:
        return _duplicate(repo, duplicate, actor_id, ip, trace_id, sync=sync)
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
        sync=sync,
        guard=guard,
    )


def _evaluate(
    manifest: dict[str, Any],
    files: dict[str, bytes],
    plan: dict[str, Any],
    report: dict[str, Any],
    plan_hash: str,
    report_sha256: str,
    validation: dict[str, Any],
    previous_round: int,
    duplicate: dict[str, Any] | None,
) -> Verdict:
    return ingest.evaluate(
        manifest=manifest,
        files=files,
        plan=plan,
        report=report,
        report_sha256=report_sha256,
        plan_hash=plan_hash,
        snapshot_hash=_snapshot_hash(report),
        previous_round=_round_floor(previous_round, duplicate, report),
        validation=validation,
    )


def _structure_verdict(validation: dict[str, Any]) -> Verdict | None:
    if validation.get("ok") is True:
        return None
    return fail(
        "STRUCTURE_INVALID",
        "教案未通过结构校验",
        {"issues": validation.get("issues", []), "ruleVersion": validation.get("ruleVersion", "")},
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


def load_package(files: dict[str, bytes]) -> tuple[dict | None, dict | None, dict | None, Verdict | None]:
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
    repo: Repo, verdict: Verdict, actor_id: int | None, ip: str, trace_id: str,
    *, sync: dict[str, Any] | None = None,
) -> ImportResult:
    if sync is not None:
        sync_log.record(repo, sync, "", "rejected", verdict.code)
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
    sync: dict[str, Any] | None = None,
    guard: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
) -> ImportResult:
    written: list[tuple[int, int]] = []

    def audit_rollback(exc: BaseException) -> None:
        # 事务已回滚：拒绝审计/冲突日志与已落盘文件都要在事务外补写/清理，否则会留下孤儿
        code = exc.code if isinstance(exc, AppError) else "INTERNAL"
        message = exc.message if isinstance(exc, AppError) else str(exc)
        details = exc.details if isinstance(exc, AppError) else {}
        for plan_id_, version_no_ in written:
            storage.remove_version_files(plan_id_, version_no_)
        audit_service.record(
            repo,
            actor_id=actor_id,
            action="sync.push.conflict" if code == "CONFLICT_STALE" and sync else "plan.import.rejected",
            target_type="plan",
            target_id="",
            detail={"code": code, "message": message, "stage": "persist", "planHash": plan_hash},
            ip=ip,
            trace_id=trace_id,
        )
        if sync is not None:
            repo.insert_sync_log(
                str(sync.get("direction") or "push"),
                str(sync.get("package_sha256") or ""),
                str(details.get("headHash") or plan_hash),
                "conflict" if code == "CONFLICT_STALE" else "rejected",
                code,
                int(sync.get("operator_id") or 0) or None,
            )

    with repo.transaction(audit_rollback):
        plan_id = repo.find_or_create_plan(owner_id, plan)
        existing = repo.find_version(plan_id, plan_hash, report_sha256)
        if existing is not None:
            return _duplicate(repo, existing, actor_id, ip, trace_id, sync=sync)
        if guard is not None:
            # 乐观锁判定放进事务内、duplicate 复检之后：并发同包时后到一方按"重复"返回 200
            guard(plan, report)
        _ensure_round(repo, plan_id, previous_round, sync, plan_hash)
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
            sync=sync,
            written=written,
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
    sync: dict[str, Any] | None = None,
    written: list[tuple[int, int]] | None = None,
) -> ImportResult:
    version_no = repo.next_version_no(plan_id)
    engine_version = engine.engine_version()
    version_id, created = repo.insert_version_or_existing(
        plan_id,
        version_no,
        json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        plan_hash,
        report_sha256,
        int(report["schemaVersion"]),
        str(report["rubricVersion"]),
        engine_version,
    )
    if not created:
        stored = repo.find_version(plan_id, plan_hash, report_sha256) or {}
        return _duplicate(repo, stored, actor_id, ip, trace_id, sync=sync)
    review_id = repo.insert_review(
        version_id,
        int(report["round"]),
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        report_sha256,
        str(report["status"]),
        str(report.get("independence") or report.get("reviewer") or "role_simulation"),
    )
    repo.insert_findings(review_id, list(report.get("findings") or []))
    repo.insert_overrides(review_id, list(report.get("overrides") or []))
    # 先推进头版本再落审查：并发下另一个请求若读到"头还是旧版"，会走 409；
    # 反过来（先落审查、后推头）会让它看到"轮次已变但头没变"，误判成 422（R3-3）。
    repo.set_current_version(plan_id, version_id)
    repo.insert_sync_event("version", plan_id, version_id)
    if written is not None:
        # 落盘发生的目录先登记：事务回滚时由 on_rollback 回调清理，避免孤儿文件
        written.append((plan_id, version_no))
    storage.store_version_files(plan_id, version_no, files)
    _audit_import(repo, plan_id, version_no, review_id, plan_hash, engine_version, actor_id, ip, trace_id)
    if sync is not None:
        sync_log.record(repo, sync, plan_hash, "created")
    return ImportResult(True, plan_id, version_no, review_id, plan_hash)


def _audit_import(
    repo: Repo, plan_id: int, version_no: int, review_id: int, plan_hash: str,
    engine_version: str, actor_id: int | None, ip: str, trace_id: str,
) -> None:
    audit_service.record(
        repo,
        actor_id=actor_id,
        action="plan.import",
        target_type="plan",
        target_id=str(plan_id),
        detail={"versionNo": version_no, "reviewId": review_id, "planHash": plan_hash, "engineVersion": engine_version},
        ip=ip,
        trace_id=trace_id,
        after_hash=plan_hash,
    )


def _duplicate(
    repo: Repo, existing: dict[str, Any], actor_id: int | None, ip: str, trace_id: str,
    *, sync: dict[str, Any] | None = None,
) -> ImportResult:
    if sync is not None:
        sync_log.record(repo, sync, str(existing.get("plan_hash") or ""), "duplicate")
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
        str(existing.get("plan_hash") or ""),
    )


def _ensure_round(
    repo: Repo, plan_id: int, previous_round: int, sync: dict[str, Any] | None, plan_hash: str
) -> None:
    if repo.last_round(plan_id) == previous_round:
        return
    if sync is not None:
        sync_log.record(repo, sync, plan_hash, "conflict", "CONFLICT_STALE")
    raise AppError("CONFLICT_STALE", "入库期间出现了新的审查轮次，请重试")
