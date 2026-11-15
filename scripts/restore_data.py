# -*- coding: utf-8 -*-
"""校验快照并恢复到目标数据目录；失败不留下半套数据。

用法：
    py -3 scripts/restore_data.py --snapshot backups/20261115T... 
    py -3 scripts/restore_data.py --snapshot <快照> --target <数据目录> --force
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data"
SUPPORTED_SCHEMA_VERSION = 15
FORMAT_VERSION = 1
REQUIRED_MANIFEST = (
    "formatVersion",
    "createdAt",
    "schemaVersion",
    "database",
    "files",
    "totals",
)


class RestoreError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: str) -> str:
    path = PurePosixPath(str(value).replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RestoreError(3, f"快照文件路径非法：{value}")
    return path.as_posix()


def load_manifest(snapshot: Path) -> dict:
    path = snapshot / "manifest.json"
    if not path.is_file():
        raise RestoreError(3, f"快照缺少 manifest.json：{snapshot}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RestoreError(3, f"manifest.json 无法解析：{exc}") from exc
    if not isinstance(manifest, dict):
        raise RestoreError(3, "manifest.json 必须是对象")
    missing = [key for key in REQUIRED_MANIFEST if key not in manifest]
    if missing:
        raise RestoreError(3, f"manifest 缺少字段：{missing}")
    if manifest.get("formatVersion") != FORMAT_VERSION:
        raise RestoreError(3, f"快照格式版本不受支持：{manifest.get('formatVersion')}")
    if int(manifest.get("schemaVersion") or 0) > SUPPORTED_SCHEMA_VERSION:
        raise RestoreError(4, f"快照结构版本 {manifest['schemaVersion']} 高于代码支持的 {SUPPORTED_SCHEMA_VERSION}")
    if not isinstance(manifest.get("files"), list) or not manifest["files"]:
        raise RestoreError(3, "manifest.files 必须是非空数组")
    return manifest


def verify_snapshot(snapshot: Path) -> dict:
    snapshot = Path(snapshot).resolve()
    manifest = load_manifest(snapshot)
    database = snapshot / "app.db"
    if not database.is_file():
        raise RestoreError(3, "快照缺少 app.db")
    declared = str((manifest.get("database") or {}).get("sha256") or "")
    actual = sha256_file(database)
    if declared != actual:
        raise RestoreError(3, "快照数据库哈希不匹配")
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        counts = {
            str(row[0]): int(connection.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        }
    finally:
        connection.close()
    if integrity != "ok":
        raise RestoreError(3, f"快照数据库完整性检查失败：{integrity}")
    if counts != (manifest["database"].get("rowCounts") or {}):
        raise RestoreError(3, "快照数据库行数与 manifest 不一致")
    for item in manifest["files"]:
        relative = _safe_relative(str(item.get("path") or ""))
        path = snapshot / relative
        if not path.is_file():
            raise RestoreError(3, f"快照缺少文件：{relative}")
        data = path.read_bytes()
        if len(data) != int(item.get("size") or -1) or hashlib.sha256(data).hexdigest() != item.get("sha256"):
            raise RestoreError(3, f"快照文件大小/哈希不匹配：{relative}")
    return manifest


def _copy_snapshot(snapshot: Path, staging: Path, manifest: dict) -> None:
    staging.mkdir(parents=True)
    for item in manifest["files"]:
        relative = _safe_relative(str(item["path"]))
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot / relative, target)


def _verify_staging(staging: Path, manifest: dict) -> None:
    database = staging / "app.db"
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        counts = {
            str(row[0]): int(connection.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        }
    finally:
        connection.close()
    if integrity != "ok":
        raise RestoreError(5, f"恢复后数据库完整性失败：{integrity}")
    if version != int(manifest["schemaVersion"]):
        raise RestoreError(5, f"恢复后结构版本 {version} 与快照 {manifest['schemaVersion']} 不一致")
    if counts != (manifest["database"].get("rowCounts") or {}):
        raise RestoreError(5, "恢复后数据库行数与快照不一致")


def restore_snapshot(snapshot: Path, target: Path, *, force: bool = False) -> dict:
    snapshot = Path(snapshot).resolve()
    target = Path(target).resolve()
    manifest = verify_snapshot(snapshot)
    if target.exists() and any(target.iterdir()) and not force:
        raise RestoreError(3, f"目标目录非空，需 --force：{target}")
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / f".restore-{uuid.uuid4().hex}"
    backup = parent / f".pre-restore-{uuid.uuid4().hex}"
    moved_backup = False
    try:
        _copy_snapshot(snapshot, staging, manifest)
        _verify_staging(staging, manifest)
        if target.exists():
            if any(target.iterdir()):
                target.replace(backup)
                moved_backup = True
            else:
                target.rmdir()
        staging.replace(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        if moved_backup and not target.exists():
            backup.replace(target)
        raise
    return {
        "ok": True,
        "target": str(target),
        "snapshot": str(snapshot),
        "backup": str(backup) if moved_backup else "",
        "rowCounts": manifest["database"].get("rowCounts") or {},
        "files": manifest["totals"].get("files", len(manifest["files"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验并恢复平台数据快照")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--target", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--force", action="store_true", help="目标目录非空时先备份再恢复")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = restore_snapshot(args.snapshot, args.target, force=args.force)
    except RestoreError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "error": exc.message}, ensure_ascii=False), file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(json.dumps({"ok": False, "code": 5, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 5
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"restored: {report['target']}")
        print(f"rows: {report['rowCounts']}")
        if report["backup"]:
            print(f"previous data: {report['backup']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
