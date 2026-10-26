# -*- coding: utf-8 -*-
"""校标结构校验。"""
from __future__ import annotations

import json
from typing import Any

from .examples import load_examples
from .model import (
    ACTIVITY_FLOW_LABELS,
    REQUIRED_FLOW,
    REQUIRED_TOP,
    RULES_VERSION,
    _activity_minutes,
    _finalize_findings,
    _nonempty,
    _normalise_text,
    _structured_activities,
    _structured_task_text,
)


def _catalog_conflicts(data: dict[str, Any]) -> list[dict[str, str]]:
    course = _normalise_text(data.get("course"))
    week = data.get("week")
    session = data.get("session")
    if not course or type(week) is not int or type(session) is not int:
        return []
    if week <= 0 or session <= 0:
        return []
    try:
        samples = load_examples()
    except (OSError, json.JSONDecodeError):
        return []
    entry: dict[str, Any] | None = None
    for _path, sample in samples:
        if _normalise_text(sample.get("course")) != course:
            continue
        if sample.get("week") == week and sample.get("session") == session:
            entry = sample
            break
    if entry is None:
        return []
    findings: list[dict[str, str]] = []
    title = _normalise_text(data.get("contentTitle"))
    catalog_title = _normalise_text(entry.get("contentTitle"))
    if title and catalog_title and title != catalog_title:
        findings.append(
            {
                "path": "contentTitle",
                "message": f"与样例目录第 {week} 周第 {session} 次的课题不一致（目录：{entry.get('contentTitle')}）",
            }
        )
    detail = _normalise_text(data.get("contentDetail"))
    catalog_detail = _normalise_text(entry.get("contentDetail"))
    if detail and catalog_detail and detail != catalog_detail:
        findings.append(
            {
                "path": "contentDetail",
                "message": f"与样例目录第 {week} 周第 {session} 次的练习套别不一致（目录：{entry.get('contentDetail')}）",
            }
        )
    return findings


def _validate_activity_rows(value: Any, path: str, issues: list[dict[str, str]]) -> None:
    rows = _structured_activities(value)
    if rows is None:
        return
    if not rows:
        issues.append({"path": path, "message": "结构化活动列表不能为空"})
        return
    for idx, row in enumerate(rows):
        row_path = f"{path}[{idx}]"
        if not _nonempty(row.get("mainContent")):
            issues.append({"path": f"{row_path}.mainContent", "message": "主要内容不能为空"})
        minutes = row.get("minutes")
        if minutes is not None and (
            isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or minutes < 0
        ):
            issues.append({"path": f"{row_path}.minutes", "message": "分钟数须为非负数字"})
        # Teacher/student/evidence are optional individually for compatibility;
        # at least one learner-facing action or verifiable output is recommended.


def validate_plan(
    data: Any,
    *,
    strict: bool = False,
    minutes_tolerance: float = 0.0,
) -> dict[str, Any]:
    warnings: list[dict[str, str]] = []
    if not isinstance(data, dict):
        return {
            "ok": False,
            "issues": [{"path": "(root)", "message": "教案必须是 JSON 对象"}],
            "warnings": [],
            "ruleVersion": RULES_VERSION,
        }

    issues: list[dict[str, str]] = []
    for key in REQUIRED_TOP:
        if key not in data or not _nonempty(data.get(key)):
            issues.append({"path": key, "message": f"{key} 不能为空"})

    week = data.get("week")
    session = data.get("session")
    if "week" in data and _nonempty(week):
        if type(week) is not int or week <= 0:
            issues.append({"path": "week", "message": "周次须为正整数"})
    if "session" in data and _nonempty(session):
        if type(session) is not int or session <= 0:
            issues.append({"path": "session", "message": "课次须为正整数"})

    sem = data.get("semester")
    if "semester" in data and _nonempty(sem):
        if type(sem) is not int or sem not in (1, 2):
            issues.append({"path": "semester", "message": "学期须为 1 或 2"})

    hours = data.get("plannedHours")
    if "plannedHours" in data and _nonempty(hours):
        if isinstance(hours, bool) or not isinstance(hours, (int, float)) or hours <= 0:
            issues.append({"path": "plannedHours", "message": "计划学时须为正数"})

    flow = data.get("activityFlow")
    if not isinstance(flow, dict):
        issues.append({"path": "activityFlow", "message": "教学活动流程必须是对象"})
    else:
        for key in REQUIRED_FLOW:
            if not _nonempty(flow.get(key)):
                label = ACTIVITY_FLOW_LABELS.get(key, key)
                issues.append({"path": f"activityFlow.{key}", "message": f"{label} 不能为空"})
            _validate_activity_rows(flow.get(key), f"activityFlow.{key}", issues)
        task_value = flow.get("taskImplementation")
        task_rows = _structured_activities(task_value)
        task_text = _structured_task_text(task_rows) if task_rows is not None else str(task_value or "")
        if task_text and ("必须完成" not in task_text and "必做" not in task_text):
            issues.append(
                {
                    "path": "activityFlow.taskImplementation",
                    "message": "工作任务实施须包含「必须完成」或「必做」任务说明",
                }
            )

    try:
        tolerance = max(0.0, float(minutes_tolerance))
    except (TypeError, ValueError):
        tolerance = 0.0
    if isinstance(flow, dict) and isinstance(hours, (int, float)) and not isinstance(hours, bool) and hours > 0:
        total, found, missing = _activity_minutes(flow)
        if missing:
            warnings.append(
                {"path": "activityFlow", "message": "部分活动未填写分钟数，无法核对合计"}
            )
        if found:
            expected = float(hours) * 45
            if abs(total - expected) > tolerance + 1e-9:
                issues.append(
                    {
                        "path": "activityFlow",
                        "message": f"活动分钟合计 {total:g} 与计划学时 {hours:g}（{expected:g} 分钟）不一致",
                    }
                )

    conflicts = _catalog_conflicts(data)
    if strict:
        issues.extend(conflicts)
    else:
        warnings.extend(conflicts)

    issues = _finalize_findings(issues)
    warnings = _finalize_findings(warnings)
    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "ruleVersion": RULES_VERSION,
        "plan": data if not issues else None,
    }
