# -*- coding: utf-8 -*-
"""任务规则：逾期判定与建课参数校验，纯函数。"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.domain.errors import AppError

STATUSES = {"draft", "reviewing", "passed", "exported"}
QUADRANTS = {
    "urgent_important",
    "important_not_urgent",
    "urgent_not_important",
    "not_urgent_not_important",
}
DEFAULT_QUADRANT = "important_not_urgent"

TASK_RANK = {"draft": 0, "reviewing": 1, "passed": 2, "exported": 3}


def validate(course: str, week: int, session: int, title: str, class_name: str) -> dict[str, Any]:
    if not str(course or "").strip() or not str(title or "").strip():
        raise AppError("PAYLOAD_REJECTED", "课程与课题不能为空")
    if not isinstance(week, int) or isinstance(week, bool) or week < 1:
        raise AppError("PAYLOAD_REJECTED", "周次必须是正整数")
    if not isinstance(session, int) or isinstance(session, bool) or session < 1:
        raise AppError("PAYLOAD_REJECTED", "课次必须是正整数")
    return {
        "course": str(course).strip(),
        "week": week,
        "session": session,
        "title": str(title).strip(),
        "class_name": str(class_name or "").strip(),
    }


def is_overdue(due_date: str | None, status: str, today: date) -> bool:
    if not due_date or status == "exported":
        return False
    return str(due_date)[:10] < today.isoformat()


def validate_quadrant(value: Any, *, default: str = DEFAULT_QUADRANT) -> str:
    quadrant = str(value or default)
    if quadrant not in QUADRANTS:
        raise AppError("PAYLOAD_REJECTED", f"未知象限：{quadrant}")
    return quadrant


def is_active(status: str, discarded_at: str | None) -> bool:
    return status not in {"passed", "exported"} and discarded_at is None


def can_touch(user: dict[str, Any], task: dict[str, Any]) -> bool:
    """本人的任务、或本组任务（组长建的任务组内教师可推进）；管理员全部。"""
    if str(user.get("role") or "") == "admin":
        return True
    if int(user.get("id") or 0) == int(task["owner_id"]):
        return True
    group = str(user.get("group_name") or "").strip()
    task_group = str(task.get("group_name") or task.get("owner_group") or "").strip()
    return bool(group) and group == task_group


def can_overwrite(user: dict[str, Any], task: dict[str, Any]) -> bool:
    """覆盖（改标题/截止）只允许本人或管理员；组内共享只读+推进（R3-F6）。"""
    return str(user.get("role") or "") == "admin" or int(user.get("id") or 0) == int(task["owner_id"])
