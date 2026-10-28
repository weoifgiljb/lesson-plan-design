# -*- coding: utf-8 -*-
"""统计口径：通过率、状态分布与轮次分布，纯函数。"""
from __future__ import annotations

from typing import Any

PASSED_STATUS = {"passed", "passed_with_override", "passed_with_accepted_minor"}


def summarize(raw: dict[str, Any]) -> dict[str, Any]:
    reviews = {str(row["key"]): int(row["total"]) for row in raw.get("reviews") or []}
    total_reviews = sum(reviews.values())
    passed = sum(count for status, count in reviews.items() if status in PASSED_STATUS)
    findings = _findings(raw.get("findings") or [])
    rounds = {
        str(int(row["key"])): int(row["total"]) for row in raw.get("rounds") or []
    }
    exports = {str(row["key"]): int(row["total"]) for row in raw.get("exports") or []}
    return {
        "totals": {
            "plans": int(raw.get("plans") or 0),
            "versions": int(raw.get("versions") or 0),
            "reviews": total_reviews,
            "findings": sum(findings["severity"].values()),
            "exports": sum(exports.values()),
        },
        "passRate": _rate(passed, total_reviews),
        "reviewStatus": reviews,
        "findingSeverity": findings["severity"],
        "findingStatus": findings["status"],
        "rounds": rounds,
        "exportStatus": exports,
    }


def _findings(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    severity: dict[str, int] = {}
    status: dict[str, int] = {}
    for row in rows:
        total = int(row["total"])
        severity[str(row["severity"])] = severity.get(str(row["severity"]), 0) + total
        status[str(row["status"])] = status.get(str(row["status"]), 0) + total
    return {"severity": severity, "status": status}


def _rate(part: int, total: int) -> float:
    return round(part / total, 4) if total else 0.0
