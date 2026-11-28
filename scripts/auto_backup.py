# -*- coding: utf-8 -*-
"""每日自动备份入口：创建快照 + 7 日/4 周保留 + 失败日志。"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from backup_data import create_snapshot, default_backup_dir, zip_path_for  # noqa: E402

AUTO_PREFIX = "auto-"


def _manifest(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def auto_snapshots(backup_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    items = []
    if not backup_dir.is_dir():
        return items
    for path in backup_dir.iterdir():
        if not path.is_dir():
            continue
        manifest = _manifest(path)
        # 目录名是 `<UTC时间戳>-<label>`，不能用 startswith("auto-") 过滤；以 manifest 的 label 为准
        if manifest is None or not str(manifest.get("label") or "").startswith(AUTO_PREFIX):
            continue
        items.append((path, manifest))
    return sorted(items, key=lambda item: str(item[1].get("createdAt") or ""), reverse=True)


def apply_retention(backup_dir: Path, keep: int = 7, weekly_keep: int = 4) -> list[str]:
    snapshots = auto_snapshots(backup_dir)
    protected = {path for path, _manifest in snapshots[:keep]}
    weeks: set[str] = set()
    for path, manifest in snapshots[keep:]:
        created = str(manifest.get("createdAt") or "")
        try:
            week = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%G-%V")
        except ValueError:
            continue
        if len(weeks) < weekly_keep and week not in weeks:
            weeks.add(week)
            protected.add(path)
    removed = []
    for path, _manifest in snapshots:
        if path in protected:
            continue
        shutil.rmtree(path, ignore_errors=True)
        zip_path_for(path).unlink(missing_ok=True)
        removed.append(path.name)
    return removed


def run(data_dir: Path, backup_dir: Path, *, keep: int, weekly_keep: int, make_zip: bool) -> dict[str, Any]:
    label = AUTO_PREFIX + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snapshot = create_snapshot(data_dir, backup_dir, label=label, make_zip=make_zip)
    removed = apply_retention(backup_dir, keep=keep, weekly_keep=weekly_keep)
    return {"ok": True, "snapshot": snapshot["path"], "label": label, "removed": removed}


def main() -> int:
    parser = argparse.ArgumentParser(description="每日自动备份")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--backup-dir", type=Path, default=default_backup_dir())
    parser.add_argument("--keep", type=int, default=7, help="保留最近 N 份每日快照")
    parser.add_argument("--weekly-keep", type=int, default=4, help="额外保留最近 N 周各一份")
    parser.add_argument("--zip", action="store_true", help="同时生成 zip")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    log = args.backup_dir / "auto-backup.log"
    try:
        args.backup_dir.mkdir(parents=True, exist_ok=True)
        payload = run(args.data_dir, args.backup_dir, keep=args.keep, weekly_keep=args.weekly_keep, make_zip=args.zip)
    except Exception as exc:  # noqa: BLE001 - 计划任务需要结构化失败日志
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "at": datetime.now(timezone.utc).isoformat()}
        log.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 3
    line = json.dumps({"ok": True, "label": payload["label"], "at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False)
    with log.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else f"backup: {payload['snapshot']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
