# -*- coding: utf-8 -*-
"""统计编排：按当前版本 + 最新一轮审查聚合 9 项指标。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.adapters import engine
from app.adapters.db.repo import Repo
from app.domain import evidence, library, stats, timerange


def summary(repo: Repo, user: dict[str, Any], *, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    raw_filters = dict(filters or {})
    window = {
        "course": raw_filters.get("course"),
        "week": raw_filters.get("week"),
        "class": raw_filters.get("class"),
        "teacher": raw_filters.get("teacher"),
        "created_from": timerange.start_of(raw_filters["date_from"]) if raw_filters.get("date_from") else None,
        "created_before": timerange.end_exclusive(raw_filters["date_to"]) if raw_filters.get("date_to") else None,
    }
    scope = library.scope_for(user)
    rows = repo.stats_plans(scope, window)
    rounds = repo.stats_rounds(sorted({int(row["plan_id"]) for row in rows}))
    records = [_record(row, rounds.get(int(row["plan_id"]), [])) for row in rows]
    minutes, basis = _export_seconds(repo.stats_exports(scope, window))
    payload = stats.build(
        records,
        _counts(repo.stats_sync(scope, window)),
        _counts(repo.stats_tasks(scope, window)),
        minutes,
        _filters_payload(raw_filters),
        export_basis=basis,
    )
    payload["scope"] = _scope_name(str(user.get("role") or ""))
    return payload


def records(
    repo: Repo,
    user: dict[str, Any],
    *,
    filters: dict[str, Any] | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    """下钻：与 summary 同一套范围/筛选，逐条返回可定位的记录。"""
    raw_filters = dict(filters or {})
    window = {
        "course": raw_filters.get("course"),
        "week": raw_filters.get("week"),
        "class": raw_filters.get("class"),
        "teacher": raw_filters.get("teacher"),
        "created_from": timerange.start_of(raw_filters["date_from"]) if raw_filters.get("date_from") else None,
        "created_before": timerange.end_exclusive(raw_filters["date_to"]) if raw_filters.get("date_to") else None,
    }
    actual_page, actual_size, offset = library.page_params(page, page_size)
    scope = library.scope_for(user)
    rows = repo.stats_plans(scope, window)
    total = len(rows)
    window_rows = rows[offset : offset + actual_size]
    rounds = repo.stats_rounds(sorted({int(row["plan_id"]) for row in window_rows}))
    items = []
    for row in window_rows:
        detail = _record(row, rounds.get(int(row["plan_id"]), []))
        items.append(
            {
                "planId": int(row["plan_id"]),
                "reviewId": int(row["review_id"]) if row.get("review_id") is not None else None,
                "course": row.get("course") or "",
                "week": int(row.get("week") or 0),
                "session": int(row.get("session") or 0),
                "teacher": row.get("teacher") or "",
                "versionNo": int(row.get("version_no") or 0),
                "reviewStatus": row.get("review_status") or "",
                "structureOk": bool(detail["structure_ok"]),
                "evidenceOk": bool(detail["evidence_ok"]),
                "openBlocking": int(detail["open_blocking"]),
                "createdAt": row.get("plan_created_at"),
            }
        )
    return {
        "items": items,
        "page": actual_page,
        "pageSize": actual_size,
        "total": total,
        "filters": _filters_payload(raw_filters),
        "scope": _scope_name(str(user.get("role") or "")),
    }


def _record(row: dict[str, Any], rounds: list[int]) -> dict[str, Any]:
    content = json.loads(row["content_json"]) if row.get("content_json") else {}
    structure_ok = bool(content) and engine.validate_plan(content).get("ok") is True
    report = json.loads(row["report_json"]) if row.get("report_json") else None
    complete = False
    open_blocking = 0
    if isinstance(report, dict):
        snapshot = report.get("planSnapshot")
        complete = evidence.evaluate(
            report,
            plan_hash=str(row["plan_hash"]),
            rounds=rounds,
            snapshot_hash=engine.plan_hash(snapshot) if isinstance(snapshot, dict) else None,
        )["complete"]
        open_blocking = sum(
            1
            for item in report.get("findings") or []
            if isinstance(item, dict)
            and item.get("status") == "open"
            and item.get("severity") in {"blocker", "major"}
        )
    return {"structure_ok": structure_ok, "evidence_ok": complete, "open_blocking": open_blocking}


def _counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {str(row["key"]): int(row["total"]) for row in rows}


def _export_seconds(rows: list[dict[str, Any]]) -> tuple[list[float], dict[str, int]]:
    """单份耗时：任务创建 → 导出完成，单位分钟（需求 BS-08/开题表 2）。

    没有关联系任务时回退到教案创建时间，这种情况单独计数，避免把两种口径混成一个均值。
    """
    minutes = []
    basis = {"task": 0, "plan": 0}
    for row in rows:
        start = datetime.fromisoformat(str(row["start_at"]))
        end = datetime.fromisoformat(str(row["export_created_at"]))
        minutes.append(max((end - start).total_seconds(), 0.0) / 60.0)
        basis["task" if int(row.get("from_task") or 0) else "plan"] += 1
    return minutes, basis


def export_csv(repo: Repo, user: dict[str, Any], *, filters: dict[str, Any] | None = None) -> str:
    """把 9 项指标导出为 CSV：分子/分母/值/单位/可用性都要看得见。"""
    payload = summary(repo, user, filters=filters)
    lines = ["key,label,numerator,denominator,value,unit,available"]
    for item in payload["metrics"]:
        value = "" if item["value"] is None else item["value"]
        lines.append(
            ",".join(
                (
                    str(item["key"]),
                    str(item["label"]),
                    str(item["numerator"]),
                    str(item["denominator"]),
                    str(value),
                    str(item["unit"]),
                    "1" if item["available"] else "0",
                )
            )
        )
    return "\n".join(lines) + "\n"


def _filters_payload(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "course": raw.get("course"),
        "week": raw.get("week"),
        "class": raw.get("class"),
        "teacher": raw.get("teacher"),
        "dateFrom": raw.get("date_from").isoformat() if raw.get("date_from") else None,
        "dateTo": raw.get("date_to").isoformat() if raw.get("date_to") else None,
    }


def _scope_name(role: str) -> str:
    if role == "admin":
        return "all"
    if role == "lead":
        return "group"
    return "own"
