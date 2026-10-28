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


def identity(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "course": str(plan.get("course") or ""),
        "week": int(plan["week"]),
        "session": int(plan["session"]),
        "title": str(plan.get("contentTitle") or ""),
    }
