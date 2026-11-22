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


#: 建课冲突文案：本人/同组可见占用者；跨组只给泛化提示，不回传任何任务信息（T1/T2）
CONFLICT_SELF = "同一班级的同一课题已存在；确认覆盖请带 confirm=true"
CONFLICT_GROUP = "该课题任务已由{owner}创建，不能覆盖"
CONFLICT_OTHER = "同一身份的课题任务已存在（其他教师），请调整课题或联系管理员"
FORBIDDEN_OVERWRITE = "只能覆盖自己创建的任务；他人任务请由本人或管理员处理"


def conflict_for(
    user: dict[str, Any], task: dict[str, Any], owner_name: str = ""
) -> tuple[str, str, dict[str, Any]]:
    """同身份任务已存在时的 409 语义：返回 (错误码, 文案, details)。

    本人可覆盖 → TASK_ALREADY_EXISTS；同组非本人 → TASK_TAKEN_BY_OTHER 且占用者可见；
    跨组（can_touch 为假）→ TASK_TAKEN_BY_OTHER 且 details 不含 taskId/ownerId/ownerName。
    """
    overwritable = can_overwrite(user, task)
    if not can_touch(user, task):
        return "TASK_TAKEN_BY_OTHER", CONFLICT_OTHER, {"canOverwrite": False}
    details = {
        "taskId": int(task["id"]),
        "ownerId": int(task["owner_id"]),
        "ownerName": owner_name,
        "canOverwrite": overwritable,
    }
    if overwritable:
        return "TASK_ALREADY_EXISTS", CONFLICT_SELF, details
    return "TASK_TAKEN_BY_OTHER", CONFLICT_GROUP.format(owner=owner_name or "其他教师"), details
