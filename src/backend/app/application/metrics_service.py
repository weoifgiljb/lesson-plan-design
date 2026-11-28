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
    export_rate = _rate(counts["exportFailed"], counts["exportTotal"])
    conflict_rate = _rate(counts["syncConflicts"], counts["syncTotal"])
    alerts = []
    if export_rate >= 0.2:
        alerts.append({"code": "EXPORT_FAILURE_RATE", "level": "warning", "message": f"导出失败率 {export_rate:.1%} 超过 20%"})
    if conflict_rate >= 0.1:
        alerts.append({"code": "SYNC_CONFLICT_RATE", "level": "warning", "message": f"同步冲突率 {conflict_rate:.1%} 超过 10%"})
    return {
        "export": {
            "total": counts["exportTotal"],
            "succeeded": counts["exportSucceeded"],
            "failed": counts["exportFailed"],
            "failureRate": export_rate,
        },
        "sync": {
            "total": counts["syncTotal"],
            "conflicts": counts["syncConflicts"],
            "conflictRate": conflict_rate,
        },
        "alerts": alerts,
        "logRetentionDays": 30,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
