# -*- coding: utf-8 -*-
"""DOCX 导出命名、备份与历史清单。"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

HISTORY_SUFFIX = ".exports.json"
BACKUP_SUFFIX = ".bak"


def history_path(plan_path: Path) -> Path:
    return plan_path.with_name(plan_path.stem + HISTORY_SUFFIX)


def load_history(plan_path: Path) -> list[dict[str, Any]]:
    path = history_path(plan_path)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def safe_title(value: str) -> str:
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "").strip())
    title = re.sub(r"\s+", " ", title).strip(" .")
    return (title or "未命名课题")[:40]


def default_output(plan: dict[str, Any], plan_path: Path, version: int) -> Path:
    week = plan.get("week")
    session = plan.get("session")
    return plan_path.parent / f"教案_{safe_title(str(plan.get('contentTitle') or ''))}_第{week}周第{session}次_v{version}.docx"


def record_history(plan_path: Path, output: Path, plan: dict[str, Any], version: int) -> Path:
    from lib import plan_hash

    path = history_path(plan_path)
    entries = load_history(plan_path)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    try:
        stored = str(output.relative_to(plan_path.parent))
    except ValueError:
        stored = str(output)
    entries.append(
        {
            "version": version,
            "exportedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "path": stored,
            "bytes": output.stat().st_size,
            "sha256": digest,
            "planHash": plan_hash(plan),
        }
    )
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path
