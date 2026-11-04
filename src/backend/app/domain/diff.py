# -*- coding: utf-8 -*-
"""教案版本差异：按字段路径给出前后值，纯函数。"""
from __future__ import annotations

from typing import Any


def diff_plans(before: Any, after: Any) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    _walk(before, after, "", changes)
    return sorted(changes, key=lambda item: item["path"])


def _walk(before: Any, after: Any, path: str, changes: list[dict[str, Any]]) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            _walk(before.get(key), after.get(key), f"{path}.{key}" if path else str(key), changes)
        return
    if isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            old = before[index] if index < len(before) else None
            new = after[index] if index < len(after) else None
            _walk(old, new, f"{path}[{index}]", changes)
        return
    if before != after:
        changes.append({"path": path or "(root)", "before": before, "after": after})


def summarize(changes: list[dict[str, Any]], limit: int = 5) -> list[str]:
    return [str(item["path"]) for item in changes[:limit]]
