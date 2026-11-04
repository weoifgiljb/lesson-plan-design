# -*- coding: utf-8 -*-
"""审查中心编排：只读列表、详情与证据链；平台不提供修改报告入口。"""
from __future__ import annotations

import json
from typing import Any

from app.adapters import engine
from app.adapters.db.repo import Repo
from app.application import audit_service
from app.domain import evidence, export_rules, library, timerange
from app.domain.errors import AppError


def list_reviews(
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
    rows, total = repo.list_reviews(library.scope_for(user), window, actual_size, offset)
    rounds_map = repo.plan_rounds_many(sorted({int(row["plan_id"]) for row in rows}))
    items = [_summary(repo, row, rounds_map.get(int(row["plan_id"]), [])) for row in rows]
    return {"items": items, "page": actual_page, "pageSize": actual_size, "total": total}


def review_detail(
    repo: Repo, user: dict[str, Any], review_id: int, *, ip: str = "", trace_id: str = ""
) -> dict[str, Any]:
    row = repo.get_review(review_id)
    if row is None:
        raise AppError("NOT_FOUND", "审查记录不存在")
    _require_visible(repo, user, row, ip, trace_id)
    report = repo.parse_report(row["report_json"])
    if report is None:
        return {
            "review": _review_header(row),
            "report": None,
            "findings": [],
            "overrides": [],
            "repairHistory": [],
            "evidence": {"items": [], "complete": False, "passed": 0, "total": 5, "gaps": ["report_unreadable"]},
        }
    chain = _chain(report, row, repo.plan_rounds(int(row["plan_id"])))
    if report.get("overrides"):
        # 查看放行记录要留痕（TC-09-03：入库、导出、放行查看各一条审计）
        audit_service.record(
            repo,
            actor_id=int(user.get("id") or 0) or None,
            action="review.read",
            target_type="review",
            target_id=str(review_id),
            detail={"planId": int(row["plan_id"]), "overrides": len(report.get("overrides") or [])},
            ip=ip,
            trace_id=trace_id,
        )
    return {
        "review": _review_header(row),
        "report": _report_payload(report),
        "findings": report.get("findings") or [],
        "overrides": report.get("overrides") or [],
        "repairHistory": report.get("repairHistory") or [],
        "evidence": chain,
    }


def _summary(repo: Repo, row: dict[str, Any], rounds: list[int]) -> dict[str, Any]:
    report = repo.parse_report(row["report_json"])
    if report is None:
        return {
            **_review_header(row),
            "evidence": {"complete": False, "passed": 0, "total": 5, "gaps": ["report_unreadable"]},
            "exportable": False,
        }
    chain = _chain(report, row, rounds)
    return {
        **_review_header(row),
        "evidence": {"complete": chain["complete"], "passed": chain["passed"], "total": chain["total"], "gaps": chain["gaps"]},
        "exportable": _exportable(report, complete=chain["complete"]),
    }


def _exportable(report: dict[str, Any], *, complete: bool) -> bool:
    """列表行的乐观可导出判定：状态白名单 + 无未关闭问题 + 证据链完整。

    证据链完整同时覆盖哈希、轮次、放行记录、独立性与状态一致五项；
    字段缺失、未知 schema/rubric 版本等仍由 export_service 的引擎门禁最终裁决。
    只是按钮默认态，判错也不能绕过服务端门禁。
    报告可能被写坏（status 是对象），这里只做类型守卫，不抛异常。
    """
    if not complete:
        return False
    status = report.get("status")
    if not isinstance(status, str) or status not in export_rules.ALLOWED_REPORT_STATUS:
        return False
    findings = report.get("findings")
    if findings is None:
        return True
    if not isinstance(findings, list):
        return False
    return not any(item.get("status") == "open" for item in findings if isinstance(item, dict))


def _chain(report: dict[str, Any], row: dict[str, Any], rounds: list[int]) -> dict[str, Any]:
    snapshot = report.get("planSnapshot")
    snapshot_hash = engine.plan_hash(snapshot) if isinstance(snapshot, dict) else None
    return evidence.evaluate(
        report,
        plan_hash=str(row["plan_hash"]),
        rounds=rounds,
        snapshot_hash=snapshot_hash,
    )


def _require_visible(
    repo: Repo, user: dict[str, Any], row: dict[str, Any], ip: str, trace_id: str
) -> None:
    allowed = library.can_view(
        str(user.get("role") or ""),
        int(user.get("id") or 0),
        str(user.get("group_name") or ""),
        int(row["owner_id"]),
        str(row["owner_group"] or ""),
    )
    if not allowed:
        audit_service.record(
            repo,
            actor_id=int(user.get("id") or 0),
            action="review.read.denied",
            target_type="review",
            target_id=str(row["review_id"]),
            detail={"role": user.get("role")},
            ip=ip,
            trace_id=trace_id,
        )
        raise AppError("FORBIDDEN", "无权访问该审查记录")


def _review_header(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "reviewId": int(row["review_id"]),
        "planId": int(row["plan_id"]),
        # 导出接口只认 planVersionId；少了它，审查中心无法把版本带进导出中心
        "planVersionId": int(row["plan_version_id"]),
        "versionNo": int(row["version_no"]),
        "round": int(row["round"]),
        "status": row["status"],
        "reviewerMode": row["reviewer_mode"],
        "reportSha256": row["report_sha256"],
        "reviewedAt": row["created_at"],
        "teacher": row["teacher"],
        "contentTitle": row["content_title"],
        "course": row["course"],
        "week": int(row["week"]),
        "session": int(row["session"]),
    }


def _report_payload(report: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schemaVersion",
        "rubricVersion",
        "toolVersion",
        "planHash",
        "round",
        "duplicateReview",
        "reviewer",
        "independence",
        "reviewedAt",
        "structuralValidation",
        "status",
        "conclusion",
        "attestation",
    )
    return {key: report.get(key) for key in keys}
