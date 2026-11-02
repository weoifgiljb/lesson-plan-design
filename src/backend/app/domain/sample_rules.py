# -*- coding: utf-8 -*-
"""样例库规则：身份提取与结构校验结果判定，纯函数。"""
from __future__ import annotations

from typing import Any

from app.domain.errors import AppError


def require_valid(validation: dict[str, Any]) -> None:
    if validation.get("ok") is not True:
        raise AppError(
            "STRUCTURE_INVALID",
            "样例未通过结构校验",
            {"issues": validation.get("issues", []), "ruleVersion": validation.get("ruleVersion", "")},
        )


def normalize_text(value: Any) -> str:
    """去首尾空白并把连续空白折叠为一个空格，避免“信息技术 ”绕过查重。"""
    return " ".join(str(value or "").split())


WEEK_RANGE = (1, 30)
SESSION_RANGE = (1, 20)


def identity(plan: dict[str, Any]) -> dict[str, Any]:
    week_value = plan.get("week")
    session_value = plan.get("session")
    if not isinstance(week_value, int) or isinstance(week_value, bool):
        raise AppError("STRUCTURE_INVALID", "周次必须是整数", {"week": week_value})
    if not isinstance(session_value, int) or isinstance(session_value, bool):
        raise AppError("STRUCTURE_INVALID", "课次必须是整数", {"session": session_value})
    week, session = int(week_value), int(session_value)
    if not WEEK_RANGE[0] <= week <= WEEK_RANGE[1]:
        raise AppError("STRUCTURE_INVALID", f"周次超出范围（{WEEK_RANGE[0]}–{WEEK_RANGE[1]}）", {"week": week})
    if not SESSION_RANGE[0] <= session <= SESSION_RANGE[1]:
        raise AppError(
            "STRUCTURE_INVALID", f"课次超出范围（{SESSION_RANGE[0]}–{SESSION_RANGE[1]}）", {"session": session}
        )
    return {
        "course": normalize_text(plan.get("course")),
        "week": week,
        "session": session,
        "title": normalize_text(plan.get("contentTitle")),
    }
