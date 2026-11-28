# -*- coding: utf-8 -*-
"""每日自动备份入口：创建快照 + 7 日/4 周保留 + 失败日志。"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from backup_data import create_snapshot, default_backup_dir, zip_path_for  # noqa: E402

AUTO_PREFIX = "auto-"
#: 定时任务在快照目录里留的独占标记；管理员手填 `auto-` 标签的快照没有它，不参与清理
AUTO_MARKER = ".auto-snapshot"
#: 升级前遗留的自动快照没有标记，按"<UTC时间戳>-auto-<时间>"名称兜底识别（只用于回收旧残留）
LEGACY_AUTO_RE = re.compile(r"-auto-\d{8}-\d{6}(?:-\d+)?$")


def _manifest(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def auto_snapshots(backup_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    marked: list[tuple[Path, dict[str, Any]]] = []
    legacy: list[tuple[Path, dict[str, Any]]] = []
    if not backup_dir.is_dir():
        return []
    for path in backup_dir.iterdir():
        if not path.is_dir():
            continue
        manifest = _manifest(path)
        if manifest is None:
            continue
        if (path / AUTO_MARKER).is_file():
            marked.append((path, manifest))
        elif LEGACY_AUTO_RE.search(path.name):
            legacy.append((path, manifest))
    # 名称兜底只回收"升级前"的残留：createdAt 必须早于最早的带标记快照，
    # 否则管理员用 `auto-<时间>` 当标签的手动快照也会被误删。
    if marked:
        boundary = min(str(manifest.get("createdAt") or "") for _path, manifest in marked)
        legacy = [
            item for item in legacy if str(item[1].get("createdAt") or "") < boundary
        ]
    else:
        legacy = []
    items = marked + legacy
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
    # 独占标记：只有定时任务创建的快照才允许被保留策略删除
    (Path(snapshot["path"]) / AUTO_MARKER).write_text("auto\n", encoding="utf-8")
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
