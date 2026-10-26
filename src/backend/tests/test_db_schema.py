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
        self.assertEqual(current_version(self.conn), 1)
        self.assertEqual(self.conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

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
