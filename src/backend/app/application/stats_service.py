# -*- coding: utf-8 -*-
"""统计编排：按角色范围聚合教案、审查、问题与导出。"""
from __future__ import annotations

from typing import Any

from app.adapters.db.repo import Repo
from app.domain import library, stats


def summary(repo: Repo, user: dict[str, Any]) -> dict[str, Any]:
    raw = repo.stats_summary(library.scope_for(user))
    payload = stats.summarize(raw)
    payload["scope"] = _scope_name(str(user.get("role") or ""))
    return payload


def _scope_name(role: str) -> str:
    if role == "admin":
        return "all"
    if role == "lead":
        return "group"
    return "own"
