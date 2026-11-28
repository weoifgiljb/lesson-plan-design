# -*- coding: utf-8 -*-
"""数据快照备份：SQLite 在线备份 + files/exports + manifest。

用法：
    py -3 scripts/backup_data.py
    py -3 scripts/backup_data.py --label before-defense --zip
    py -3 scripts/backup_data.py --data-dir <数据目录> --backup-dir <快照根>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data"
DEFAULT_BACKUP = ROOT / "backups"
FORMAT_VERSION = 1
APP_VERSION = "dev"
EXPORT_SUBDIRS = ("files", "exports")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return {str(row[0]): int(conn.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0]) for row in rows}


def _copy_tree(source: Path, data_dir: Path, snapshot: Path, *, skip: set[Path]) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    if not source.is_dir():
        return files
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        resolved = path.resolve()
        if resolved in skip:
            continue
        relative = path.relative_to(data_dir)
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        files.append(
            {
                "path": relative.as_posix(),
                "size": target.stat().st_size,
                "sha256": sha256_file(target),
            }
        )
    return files


def _snapshot_name(backup_dir: Path, label: str = "") -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{stamp}-{label}" if label else stamp
    candidate = backup_dir / stem
    index = 1
    while candidate.exists():
        candidate = backup_dir / f"{stem}-{index}"
        index += 1
    return candidate


def create_snapshot(
    data_dir: Path,
    backup_dir: Path,
    *,
    label: str = "",
    include_exports: bool = True,
    make_zip: bool = False,
) -> dict[str, object]:
    data_dir = Path(data_dir).resolve()
    backup_dir = Path(backup_dir).resolve()
    database = data_dir / "app.db"
    if not database.is_file():
        raise FileNotFoundError(f"数据库不存在：{database}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = _snapshot_name(backup_dir, label)
    temporary = backup_dir / f".tmp-{uuid.uuid4().hex}"
    temporary.mkdir()
    try:
        source = sqlite3.connect(str(database))
        destination = sqlite3.connect(str(temporary / "app.db"))
        try:
            source.backup(destination)
            integrity = str(destination.execute("PRAGMA integrity_check").fetchone()[0])
            schema_version = int(destination.execute("PRAGMA user_version").fetchone()[0])
            counts = table_counts(destination)
        finally:
            destination.close()
            source.close()
        if integrity != "ok":
            raise RuntimeError(f"数据库完整性检查失败：{integrity}")

        skip = {temporary, target}
        copied: list[dict[str, object]] = []
        for subdir in EXPORT_SUBDIRS:
            if subdir == "exports" and not include_exports:
                continue
            copied.extend(_copy_tree(data_dir / subdir, data_dir, temporary, skip=skip))
        copied.append(
            {
                "path": "app.db",
                "size": (temporary / "app.db").stat().st_size,
                "sha256": sha256_file(temporary / "app.db"),
            }
        )
        copied.sort(key=lambda item: str(item["path"]))
        manifest = {
            "formatVersion": FORMAT_VERSION,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "label": label,
            "appVersion": APP_VERSION,
            "schemaVersion": schema_version,
            "database": {
                "sha256": sha256_file(temporary / "app.db"),
                "rowCounts": counts,
                "integrity": integrity,
            },
            "files": copied,
            "totals": {
                "files": len(copied),
                "bytes": sum(int(item["size"]) for item in copied),
            },
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(target)
        payload: dict[str, object] = {"ok": True, "path": str(target), "manifest": manifest}
        if make_zip:
            zip_path = target.with_suffix(".zip")
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(target.rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(target).as_posix())
            payload["zip"] = str(zip_path)
        return payload
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def default_backup_dir() -> Path:
    return Path(os.environ.get("LPP_BACKUP_DIR", str(DEFAULT_BACKUP)))


def main() -> int:
    parser = argparse.ArgumentParser(description="备份平台数据目录")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--backup-dir", type=Path, default=None)
    parser.add_argument("--label", default="")
    parser.add_argument("--no-exports", action="store_true", help="不备份 exports/")
    parser.add_argument("--zip", action="store_true", help="同时生成 zip")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        payload = create_snapshot(
            args.data_dir,
            args.backup_dir or default_backup_dir(),
            label=args.label,
            include_exports=not args.no_exports,
            make_zip=args.zip,
        )
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        manifest = payload["manifest"]
        print(f"snapshot: {payload['path']}")
        print(f"files: {manifest['totals']['files']}，bytes: {manifest['totals']['bytes']}")
        print(f"database: {manifest['database']['rowCounts']}")
        if payload.get("zip"):
            print(f"zip: {payload['zip']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
