# -*- coding: utf-8 -*-
"""任务规则：逾期判定与建课参数校验，纯函数。"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.domain.errors import AppError

STATUSES = {"draft", "reviewing", "passed", "exported"}
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
