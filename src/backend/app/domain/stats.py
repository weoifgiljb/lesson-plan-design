# -*- coding: utf-8 -*-
"""统计口径：9 项指标均带分子、分母与筛选条件；空分母返回 null。"""
from __future__ import annotations

from typing import Any


def build(
    records: list[dict[str, Any]],
    sync_counts: dict[str, int],
    task_counts: dict[str, int],
    export_seconds: list[float],
    filters: dict[str, Any],
) -> dict[str, Any]:
    plans = len(records)
    structure_ok = sum(1 for item in records if item["structure_ok"])
    defects = sum(int(item["open_blocking"]) for item in records)
    evidence_ok = sum(1 for item in records if item["evidence_ok"])
    sync_total = sum(sync_counts.values())
    sync_ok = sync_counts.get("created", 0) + sync_counts.get("duplicate", 0)
    tasks_total = sum(task_counts.values())
    tasks_done = task_counts.get("exported", 0)
    return {
        "metrics": [
            _metric("structure_rate", "结构合规率", structure_ok, plans, filters),
            _metric("gold_standard", "金标准贴近分", 0, 0, filters, available=False),
            _metric("defect_density", "闭环缺陷密度", defects, plans, filters),
            _metric("evidence_rate", "证据链完整率", evidence_ok, plans, filters),
            _metric("sync_consistency", "双端数据一致率", sync_ok, sync_total, filters,
                    available=sync_total > 0),
            _metric("task_completion", "平台任务完成率", tasks_done, tasks_total, filters,
                    available=tasks_total > 0),
            _metric("expert_score", "专家评分", 0, 0, filters, available=False),
            _metric("export_seconds", "单份耗时", sum(export_seconds), len(export_seconds),
                    filters, unit="分钟", available=bool(export_seconds)),
            _metric("availability", "平台可用性", 0, 0, filters, available=False),
        ],
        "filters": filters,
    }


def _metric(
    key: str,
    label: str,
    numerator: int,
    denominator: int,
    filters: dict[str, Any],
    *,
    unit: str = "",
    available: bool = True,
) -> dict[str, Any]:
    value = round(numerator / denominator, 4) if available and denominator else None
    return {
        "key": key,
        "label": label,
        "numerator": numerator if available else 0,
        "denominator": denominator if available else 0,
        "value": value,
        "unit": unit,
        "available": bool(available),
        "filters": filters,
    }
