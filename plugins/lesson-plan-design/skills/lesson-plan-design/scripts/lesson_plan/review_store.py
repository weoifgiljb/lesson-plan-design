# -*- coding: utf-8 -*-
"""审查报告文件读写。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .jsonio import dump, load_json


def default_review_path(plan_path: Path) -> Path:
    return plan_path.with_suffix(".review.json")


def load_review_report(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("审查报告必须是 JSON 对象")
    return data


def save_review_report(path: Path, report: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(dump(report) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path

