# -*- coding: utf-8 -*-
"""数据库结构修复：早期谱系（fe-02 的 v2）对齐到当前 SCHEMA_VERSION。"""
from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from support import tempdir

from app.adapters.db import repair
from app.adapters.db.connection import SCHEMA_PATH, SCHEMA_VERSION, current_version, initialize

# 把当前 schema 的 task 表退回 v1/v2 谱系：唯一键含 owner、缺归属列
LEGACY_TASK_SQL = """
DROP TABLE task;
CREATE TABLE task (
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
);
"""

SEED_SQL = """
INSERT INTO user (username, display_name, group_name, role, password_hash, created_at)
VALUES ('t1', '张老师', '计算机', 'teacher', 'x', '2026-10-26T00:00:00+00:00');
INSERT INTO plan (owner_id, content_title, week, session, course, created_at)
VALUES (1, '一级考证辅导2', 2, 1, '信息技术', '2026-10-26T00:00:00+00:00');
INSERT INTO plan_version (plan_id, version_no, content_json, plan_hash, schema_version,
                          rubric_version, created_at)
VALUES (1, 1, '{}', 'hash-1', 1, '1.0', '2026-10-26T00:00:00+00:00');
INSERT INTO review (plan_version_id, round, report_json, report_sha256, status, reviewer_mode, created_at)
VALUES (1, 1, '{}', 'report-1', 'passed', 'native', '2026-10-26T00:00:00+00:00');
INSERT INTO task (course, week, session, title, class_name, owner_id, status, created_at)
VALUES ('信息技术', 2, 1, '课题A', '计算机1班', 1, 'draft', '2026-10-26T00:00:00+00:00');
INSERT INTO task (course, week, session, title, class_name, owner_id, status, created_at)
VALUES ('信息技术', 2, 1, '课题B', '计算机1班', 1, 'draft', '2026-10-26T00:00:00+00:00');
"""


class TestRepairSchema(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self.db = Path(self.root) / "legacy.db"

    def tearDown(self) -> None:
        self._tmp.__exit__(None, None, None)

    def _legacy_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db, isolation_level=None)
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.executescript(LEGACY_TASK_SQL)
        conn.executescript(SEED_SQL)
        conn.execute("PRAGMA user_version=2")
        return conn

    def test_inspect_reports_gaps(self) -> None:
        conn = self._legacy_db()
        try:
            state = repair.inspect(conn)
            self.assertEqual(state["version"], 2)
            self.assertTrue(state["needs_repair"])
            self.assertIn("plan_version.report_sha256", state["missing_columns"])
            self.assertIn("task.group_name", state["missing_columns"])
            self.assertFalse(state["task_key_ok"])
            self.assertEqual(state["task_key"], ("owner_id", "course", "week", "session", "class_name", "title"))
        finally:
            conn.close()

    def test_repair_aligns_schema_and_keeps_data(self) -> None:
        conn = self._legacy_db()
        try:
            repair.repair(conn)  # 脚本自己收敛：建表、补列、补索引、重建任务键
            state = repair.inspect(conn)
            self.assertEqual(state["version"], SCHEMA_VERSION)
            self.assertEqual(state["missing_columns"], [])
            self.assertEqual(state["missing_tables"], [])
            self.assertEqual(state["missing_indexes"], [])
            self.assertTrue(state["task_key_ok"])
            self.assertFalse(state["needs_repair"])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM task").fetchone()[0], 2)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM plan_version WHERE report_sha256 = 'report-1'").fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute("SELECT group_name FROM task WHERE title = '课题A'").fetchone()[0], "计算机"
            )
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
            # 唯一键生效：同班同课题再插入要被拒
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO task (course, week, session, title, class_name, owner_id, status, created_at)"
                    " VALUES ('信息技术', 2, 1, '课题A', '计算机1班', 1, 'draft', '2026-10-26T00:00:00+00:00')"
                )
        finally:
            conn.close()

    def test_repair_is_idempotent(self) -> None:
        conn = self._legacy_db()
        try:
            repair.repair(conn)
            second = repair.repair(conn)
            self.assertFalse(second["rebuilt_task"])
            self.assertEqual(repair.inspect(conn)["version"], SCHEMA_VERSION)
        finally:
            conn.close()

    def test_initialize_after_repair_is_noop(self) -> None:
        conn = self._legacy_db()
        try:
            repair.repair(conn)
            initialize(conn)  # 版本已到位，不应再跑迁移或报错
            self.assertEqual(current_version(conn), SCHEMA_VERSION)
        finally:
            conn.close()
