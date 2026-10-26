# -*- coding: utf-8 -*-
"""样例库加载与索引校验。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .jsonio import load_json
from .model import EXAMPLES_DIR, plan_hash


def load_examples() -> list[tuple[Path, dict[str, Any]]]:
    items: list[tuple[Path, dict[str, Any]]] = []
    if not EXAMPLES_DIR.is_dir():
        return items
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        items.append((path, load_json(path)))
    return items


def example_entries(directory: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    root = Path(directory) if directory is not None else EXAMPLES_DIR
    index_path = root / "index.json"
    index = load_json(index_path) if index_path.is_file() else {"examples": []}
    indexed = {
        str(item.get("file")): item
        for item in index.get("examples", [])
        if isinstance(item, dict) and item.get("file")
    }
    entries: list[dict[str, Any]] = []
    files: set[str] = set()
    for path in sorted(root.glob("*.json")):
        if path.name == "index.json":
            continue
        plan = load_json(path)
        expected = indexed.get(path.name)
        entries.append({
            "file": path.name,
            "plan": plan,
            "index": expected,
            "stale": expected is None or expected.get("planHash") != plan_hash(plan),
        })
        files.add(path.name)
    return entries, sorted(set(indexed) - files)


def check_examples(directory: Path | None = None) -> dict[str, Any]:
    entries, extra = example_entries(directory)
    errors: list[str] = []
    stale: list[str] = []
    missing: list[str] = []
    fields = ("course", "week", "session", "contentTitle")
    for entry in entries:
        name = entry["file"]
        if entry["index"] is None:
            missing.append(name)
            errors.append(f"index.json 缺少样例：{name}")
            continue
        if entry["stale"]:
            stale.append(name)
            errors.append(f"样例哈希已过期：{name}")
            continue
        for field in fields:
            if entry["index"].get(field) != entry["plan"].get(field):
                errors.append(f"样例元信息不一致：{name} 的 {field}")
    for name in extra:
        errors.append(f"index.json 引用了不存在的样例：{name}")
    return {
        "ok": not errors,
        "count": len(entries),
        "errors": errors,
        "stale": stale,
        "missing": missing,
        "extra": extra,
    }

