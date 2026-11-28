# -*- coding: utf-8 -*-
"""数据目录实例标记与启动状态：区分首装、旧库、数据丢失与外来目录。"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTANCE_NAME = ".instance.json"
FORMAT_VERSION = 1
ALLOW_INIT_ENV = "LPP_ALLOW_INIT"

# 表名来自固定白名单，避免在 execute 里拼接动态 SQL（BSEC-02）
TABLE_COUNTS = {
    "user": "SELECT COUNT(*) FROM user",
    "user_session": "SELECT COUNT(*) FROM user_session",
    "task": "SELECT COUNT(*) FROM task",
    "plan": "SELECT COUNT(*) FROM plan",
    "plan_version": "SELECT COUNT(*) FROM plan_version",
    "review": "SELECT COUNT(*) FROM review",
    "finding": "SELECT COUNT(*) FROM finding",
    "override": "SELECT COUNT(*) FROM override",
    "export_job": "SELECT COUNT(*) FROM export_job",
    "sample": "SELECT COUNT(*) FROM sample",
    "asset": "SELECT COUNT(*) FROM asset",
    "sync_log": "SELECT COUNT(*) FROM sync_log",
    "sync_event": "SELECT COUNT(*) FROM sync_event",
    "audit_log": "SELECT COUNT(*) FROM audit_log",
    "deletion_request": "SELECT COUNT(*) FROM deletion_request",
    "notification": "SELECT COUNT(*) FROM notification",
}


class DataUnavailable(RuntimeError):
    """数据库不可用时由启动/健康检查报告，调用方据此返回 503。"""


def instance_path(data_dir: Path) -> Path:
    return Path(data_dir) / INSTANCE_NAME


def read_instance(data_dir: Path) -> dict[str, Any] | None:
    path = instance_path(data_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _marker_state(data_dir: Path) -> tuple[str, dict[str, Any] | None]:
    """区分"没有标记/标记损坏/正常"，不能把损坏当首装：否则会静默覆盖 instanceId。"""
    path = instance_path(data_dir)
    if not path.is_file():
        return "missing", None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "corrupt", None
    if not isinstance(data, dict):
        return "corrupt", None
    return "ok", data


def read_instance(data_dir: Path) -> dict[str, Any] | None:
    return _marker_state(data_dir)[1]


def write_instance(data_dir: Path, schema_version: int) -> dict[str, Any]:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    state, existing = _marker_state(data_dir)
    if state == "corrupt" and os.environ.get(ALLOW_INIT_ENV, "0") != "1":
        raise DataUnavailable(
            "实例标记 .instance.json 损坏；请从快照恢复，或确认后用 LPP_ALLOW_INIT=1 重建"
        )
    if existing is not None:
        return existing
    payload = {
        "formatVersion": FORMAT_VERSION,
        "instanceId": uuid.uuid4().hex,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "schemaVersion": int(schema_version),
    }
    path = instance_path(data_dir)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)
    return payload


def _row_counts(database: Path) -> dict[str, int]:
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        counts: dict[str, int] = {}
        for row in rows:
            name = str(row[0])
            sql = TABLE_COUNTS.get(name)
            if sql is None:
                continue
            counts[name] = int(connection.execute(sql).fetchone()[0])
        return counts
    finally:
        connection.close()


def _latest_backup_at() -> str | None:
    root = Path(os.environ.get("LPP_BACKUP_DIR", str(Path(__file__).resolve().parents[5] / "backups")))
    if not root.is_dir():
        return None
    times: list[str] = []
    for path in root.glob("*/manifest.json"):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            value = manifest.get("createdAt")
            if isinstance(value, str):
                times.append(value)
        except (OSError, json.JSONDecodeError):
            continue
    return max(times) if times else None


def status(data_dir: Path, db_path: Path, *, schema_version: int | None = None) -> dict[str, Any]:
    data_dir = Path(data_dir)
    db_path = Path(db_path)
    marker_state, marker = _marker_state(data_dir)
    db_exists = db_path.is_file()
    allow_init = os.environ.get(ALLOW_INIT_ENV, "0") == "1"
    payload: dict[str, Any] = {
        "status": "ok",
        "message": "",
        "data": {
            "dir": data_dir.name,
            "db": db_path.name,
            "schemaVersion": int(marker.get("schemaVersion") or 0) if marker else 0,
            "instanceId": str(marker.get("instanceId") or "") if marker else "",
            "lastBackupAt": _latest_backup_at(),
            "rowCounts": {},
        },
    }
    if marker_state == "corrupt":
        payload.update(
            status="corrupt",
            message="实例标记 .instance.json 损坏，疑似拷贝不完整或磁盘错误；请从快照恢复，"
            "确认后可用 LPP_ALLOW_INIT=1 重建（会生成新的 instanceId）",
        )
        if allow_init:
            payload["status"] = "init-override"
        return payload
    if marker is not None and not db_exists:
        payload.update(
            status="missing",
            message="实例标记存在但数据库缺失，疑似数据丢失；请从快照恢复，不要直接启动",
            data={**payload["data"], "recovery": "py -3 scripts/restore_data.py --snapshot <快照> --force"},
        )
        if allow_init:
            payload["status"] = "init-override"
        return payload
    if marker is None and not db_exists:
        if any(data_dir.iterdir()) if data_dir.is_dir() else False:
            payload.update(
                status="foreign",
                message="数据目录非空但没有实例标记，疑似从别处拷贝；确认后设置 LPP_ALLOW_INIT=1 再启动",
            )
            if allow_init:
                payload["status"] = "init-override"
        else:
            payload["status"] = "new"
        return payload
    if marker is None and db_exists:
        payload["status"] = "legacy"
    if db_exists:
        try:
            connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
            try:
                version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            finally:
                connection.close()
            payload["data"]["schemaVersion"] = version
            payload["data"]["rowCounts"] = _row_counts(db_path)
        except (OSError, sqlite3.Error) as exc:
            payload.update(status="corrupt", message=f"数据库不可读：{exc}")
    if schema_version is not None and marker is None and db_exists and payload["status"] == "legacy":
        payload["data"]["schemaVersion"] = int(schema_version)
    return payload


def ensure_ready(data_dir: Path, db_path: Path, *, schema_version: int) -> dict[str, Any]:
    """启动前检查；允许首装/旧库/显式 override，其余状态抛 DataUnavailable。"""
    current = status(data_dir, db_path, schema_version=schema_version)
    if current["status"] in {"missing", "foreign", "corrupt"}:
        raise DataUnavailable(current["message"] or current["status"])
    return current
