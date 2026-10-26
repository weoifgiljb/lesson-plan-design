# -*- coding: utf-8 -*-
"""SQLite 连接与建库迁移：WAL、外键、忙等超时、user_version 版本号。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import db_path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SCHEMA_VERSION = 1


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


def initialize(conn: sqlite3.Connection) -> None:
    version = current_version(conn)
    if version == 0:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute("PRAGMA user_version=1")


def open_database(path: Path | None = None) -> sqlite3.Connection:
    conn = connect(path)
    initialize(conn)
    return conn
