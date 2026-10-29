# -*- coding: utf-8 -*-
"""SQLite 连接与建库迁移：WAL、外键、忙等超时、user_version 版本号。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import db_path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SCHEMA_VERSION = 2


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
        conn.execute("PRAGMA user_version=2")
        return
    if version < SCHEMA_VERSION:
        _migrate_task_identity(conn)
        conn.execute("PRAGMA user_version=2")


def _migrate_task_identity(conn: sqlite3.Connection) -> None:
    """v1 -> v2：任务唯一键加入 owner/title，允许同班不同课、不同教师同课。"""
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            """
            CREATE TABLE task_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course TEXT NOT NULL,
                week INTEGER NOT NULL,
                session INTEGER NOT NULL,
                title TEXT NOT NULL,
                class_name TEXT NOT NULL DEFAULT '',
                owner_id INTEGER NOT NULL REFERENCES user (id),
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'reviewing', 'passed', 'exported')),
                created_at TEXT NOT NULL,
                UNIQUE (owner_id, course, week, session, class_name, title)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO task_new (id, course, week, session, title, class_name, owner_id, due_date, status, created_at)
                SELECT id, course, week, session, title, class_name, owner_id, due_date, status, created_at FROM task
            """
        )
        conn.execute("DROP TABLE task")
        conn.execute("ALTER TABLE task_new RENAME TO task")
        conn.execute("COMMIT")
    finally:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        conn.execute("PRAGMA foreign_keys=ON")


def open_database(path: Path | None = None) -> sqlite3.Connection:
    conn = connect(path)
    initialize(conn)
    return conn
