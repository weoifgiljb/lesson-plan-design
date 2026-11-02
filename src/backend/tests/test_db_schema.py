# -*- coding: utf-8 -*-
"""数据库结构与不可变约束。"""
from __future__ import annotations

import sqlite3
import unittest

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import current_version, open_database
from app.adapters import clock


class TestDatabaseSchema(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.conn = open_database(self.root / "app.db")

    def tearDown(self) -> None:
        self.conn.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _seed(self) -> tuple[int, int, int]:
        user = self.conn.execute(
            "INSERT INTO user (username, display_name, role, password_hash, created_at)"
            " VALUES ('t1', '张老师', 'teacher', 'x', '2026-10-26T00:00:00+00:00')"
        ).lastrowid
        plan = self.conn.execute(
            "INSERT INTO plan (owner_id, content_title, week, session, course, created_at)"
            " VALUES (?, '课题', 2, 1, '信息技术', '2026-10-26T00:00:00+00:00')",
            (user,),
        ).lastrowid
        version = self.conn.execute(
            "INSERT INTO plan_version (plan_id, version_no, content_json, plan_hash, schema_version,"
            " rubric_version, created_at) VALUES (?, 1, '{}', 'hash', 1, '1.0', ?)",
            (plan, clock.now_iso()),
        ).lastrowid
        return int(user), int(plan), int(version)

    def test_schema_version_and_pragmas(self) -> None:
        self.assertEqual(current_version(self.conn), 3)
        self.assertEqual(self.conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_v2_database_migrates_to_board_schema(self) -> None:
        path = self.root / "v2.db"
        connection = sqlite3.connect(path)
        connection.executescript(
            """
            CREATE TABLE user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                group_name TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE task (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course TEXT NOT NULL,
                week INTEGER NOT NULL,
                session INTEGER NOT NULL,
                title TEXT NOT NULL,
                class_name TEXT NOT NULL DEFAULT '',
                owner_id INTEGER NOT NULL REFERENCES user (id),
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                UNIQUE (owner_id, course, week, session, class_name, title)
            );
            INSERT INTO user (username, display_name, role, password_hash, created_at)
                VALUES ('t1', '张老师', 'teacher', 'x', '2026-10-30T00:00:00+00:00');
            INSERT INTO task (course, week, session, title, class_name, owner_id, due_date, status, created_at)
                VALUES ('信息技术', 3, 1, '旧任务', '计算机1班', 1, '2020-01-01', 'draft',
                        '2026-10-30T00:00:00+00:00');
            PRAGMA user_version=2;
            """
        )
        connection.close()

        migrated = open_database(path)
        try:
            self.assertEqual(current_version(migrated), 3)
            columns = {row[1] for row in migrated.execute("PRAGMA table_info(task)")}
            self.assertTrue({"quadrant", "board_position", "board_version", "discarded_at"} <= columns)
            row = migrated.execute("SELECT * FROM task WHERE id = 1").fetchone()
            self.assertEqual(row["quadrant"], "urgent_important")
            self.assertEqual(row["board_position"], 1)
            self.assertEqual(row["board_version"], 0)
            self.assertIsNone(row["discarded_at"])
        finally:
            migrated.close()

    def test_task_identity_allows_same_class_different_title(self) -> None:
        user, _, _ = self._seed()
        self.conn.execute(
            "INSERT INTO task (course, week, session, title, class_name, owner_id, status, created_at)"
            " VALUES ('信息技术', 3, 1, '第一课', '计算机1班', ?, 'draft', ?)",
            (user, clock.now_iso()),
        )
        self.conn.execute(
            "INSERT INTO task (course, week, session, title, class_name, owner_id, status, created_at)"
            " VALUES ('信息技术', 3, 1, '第二课', '计算机1班', ?, 'draft', ?)",
            (user, clock.now_iso()),
        )
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM task WHERE week = 3").fetchone()[0], 2
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO task (course, week, session, title, class_name, owner_id, status, created_at)"
                " VALUES ('信息技术', 3, 1, '第二课', '计算机1班', ?, 'draft', ?)",
                (user, clock.now_iso()),
            )

    def test_plan_version_is_immutable(self) -> None:
        _, _, version = self._seed()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE plan_version SET plan_hash = 'other' WHERE id = ?", (version,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM plan_version WHERE id = ?", (version,))

    def test_audit_log_is_append_only(self) -> None:
        audit = self.conn.execute(
            "INSERT INTO audit_log (action, target_type, created_at) VALUES ('x', 'y', ?)",
            (clock.now_iso(),),
        ).lastrowid
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE audit_log SET action = 'z' WHERE id = ?", (audit,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM audit_log WHERE id = ?", (audit,))

    def test_foreign_keys_and_role_check(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO plan (owner_id, content_title, week, session, course, created_at)"
                " VALUES (999, 'x', 1, 1, 'c', ?)",
                (clock.now_iso(),),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO user (username, display_name, role, password_hash, created_at)"
                " VALUES ('u2', 'u2', 'root', 'x', ?)",
                (clock.now_iso(),),
            )

    def test_plan_identity_is_unique(self) -> None:
        user, _, _ = self._seed()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO plan (owner_id, content_title, week, session, course, created_at)"
                " VALUES (?, '课题', 2, 1, '信息技术', ?)",
                (user, clock.now_iso()),
            )

    def test_session_token_is_unique(self) -> None:
        user, _, _ = self._seed()
        expired = "2026-10-27T00:00:00+00:00"
        self.conn.execute(
            "INSERT INTO user_session (user_id, token_hash, csrf_token, created_at, expires_at)"
            " VALUES (?, 'abc', 'csrf', ?, ?)",
            (user, clock.now_iso(), expired),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO user_session (user_id, token_hash, csrf_token, created_at, expires_at)"
                " VALUES (?, 'abc', 'csrf', ?, ?)",
                (user, clock.now_iso(), expired),
            )


if __name__ == "__main__":
    unittest.main()
