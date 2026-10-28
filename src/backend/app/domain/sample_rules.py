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


def identity(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "course": normalize_text(plan.get("course")),
        "week": int(plan["week"]),
        "session": int(plan["session"]),
        "title": normalize_text(plan.get("contentTitle")),
    }
