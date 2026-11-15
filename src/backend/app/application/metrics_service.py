# -*- coding: utf-8 -*-
"""运维指标：入库/导出/同步失败率。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.adapters.db.repo import Repo


def _rate(part: int, total: int) -> float:
    return round(part / total, 4) if total else 0.0


def ops(repo: Repo) -> dict[str, Any]:
    counts = repo.ops_metrics()
    return {
        "export": {
            "total": counts["exportTotal"],
            "succeeded": counts["exportSucceeded"],
            "failed": counts["exportFailed"],
            "failureRate": _rate(counts["exportFailed"], counts["exportTotal"]),
        },
        "sync": {
            "total": counts["syncTotal"],
            "conflicts": counts["syncConflicts"],
            "conflictRate": _rate(counts["syncConflicts"], counts["syncTotal"]),
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
