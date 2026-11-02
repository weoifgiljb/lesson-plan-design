# -*- coding: utf-8 -*-
"""SQLite 连接与建库迁移：WAL、外键、忙等超时、user_version 版本号。"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from app.config import db_path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
SCHEMA_VERSION = 10
MIGRATION_NAME = re.compile(r"^(\d{4})_.*\.sql$")


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    # 单进程内多线程共享一个连接：写事务由 Repo 的写锁串行化。
    conn = sqlite3.connect(str(target), timeout=5.0, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def available_migrations() -> dict[int, Path]:
    found: dict[int, Path] = {}
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = MIGRATION_NAME.match(path.name)
        if match:
            found[int(match.group(1))] = path
    return found


def initialize(conn: sqlite3.Connection) -> None:
    version = current_version(conn)
    if version == 0:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute("PRAGMA user_version=1")
        version = 1
    if version > SCHEMA_VERSION:
        raise RuntimeError(f"数据库结构版本 {version} 高于代码支持的 {SCHEMA_VERSION}")
    migrations = available_migrations()
    for target in range(version + 1, SCHEMA_VERSION + 1):
        script = migrations.get(target)
        if script is None:
            raise RuntimeError(f"缺少迁移脚本 {target:04d}_*.sql")
        conn.executescript(script.read_text(encoding="utf-8"))
        set_version(conn, target)


_VERSION_SQL = {n: f"PRAGMA user_version={n}" for n in range(1, 100)}


def set_version(conn: sqlite3.Connection, version: int) -> None:
    """推进 user_version：PRAGMA 不支持参数绑定，这里只走内部白名单常量。"""
    sql = _VERSION_SQL.get(int(version))
    if sql is None:
        raise RuntimeError(f"迁移版本号超出范围：{version}")
    conn.execute(sql)


def open_database(path: Path | None = None) -> sqlite3.Connection:
    conn = connect(path)
    initialize(conn)
    return conn
