# -*- coding: utf-8 -*-
"""数据库结构与不可变约束。"""
from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import SCHEMA_VERSION, current_version, initialize, open_database
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
        self.assertEqual(current_version(self.conn), SCHEMA_VERSION)
        self.assertEqual(self.conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_migration_adds_report_hash_and_override_scope(self) -> None:
        columns = [row[1] for row in self.conn.execute("PRAGMA table_info(plan_version)")]
        self.assertIn("report_sha256", columns)
        indexes = {row[0] for row in self.conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        self.assertIn("ux_plan_version_report", indexes)
        override_columns = [row[1] for row in self.conn.execute("PRAGMA table_info(override)")]
        self.assertIn("review_id", override_columns)

    def test_migrations_add_sync_event_and_feature_columns(self) -> None:
        tables = {row[0] for row in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("sync_event", tables)
        sample_columns = [row[1] for row in self.conn.execute("PRAGMA table_info(sample)")]
        self.assertIn("score", sample_columns)
        export_columns = [row[1] for row in self.conn.execute("PRAGMA table_info(export_job)")]
        self.assertIn("report_sha256", export_columns)
        task_columns = [row[1] for row in self.conn.execute("PRAGMA table_info(task)")]
        self.assertIn("assignee_id", task_columns)

    def test_v1_database_upgrades_to_latest(self) -> None:
        target = self.root / "legacy.db"
        conn = sqlite3.connect(str(target), isolation_level=None)
        try:
            conn.executescript(
                Path(__file__).resolve().parents[1].joinpath("app/adapters/db/schema.sql").read_text(encoding="utf-8")
            )
            conn.execute("PRAGMA user_version=1")
            self.assertEqual(current_version(conn), 1)
            initialize(conn)
            self.assertEqual(current_version(conn), SCHEMA_VERSION)
            columns = [row[1] for row in conn.execute("PRAGMA table_info(plan_version)")]
            self.assertIn("report_sha256", columns)
        finally:
            conn.close()

    def test_v1_upgrade_keeps_data_and_attributes_overrides(self) -> None:
        # R3-4/R3-2：带数据的 v1 库要能升级，且同名哈希的两个教案各自挂到自己的审查
        target = self.root / "legacy-data.db"
        conn = sqlite3.connect(str(target), isolation_level=None)
        try:
            conn.executescript(
                Path(__file__).resolve().parents[1]
                .joinpath("app/adapters/db/schema.sql")
                .read_text(encoding="utf-8")
            )
            conn.execute("PRAGMA user_version=1")
            conn.executescript(
                "INSERT INTO user (id, username, display_name, role, password_hash, created_at)"
                " VALUES (1, 't1', '张老师', 'teacher', 'x', '2026-10-26'),"
                "        (2, 't2', '李老师', 'teacher', 'x', '2026-10-26');"
                "INSERT INTO plan (id, owner_id, content_title, week, session, course, created_at)"
                " VALUES (1, 1, '课题', 2, 1, '信息技术', '2026-10-26'),"
                "        (2, 2, '课题', 2, 1, '信息技术', '2026-10-26');"
                "INSERT INTO plan_version (id, plan_id, version_no, content_json, plan_hash,"
                " schema_version, rubric_version, created_at)"
                " VALUES (1, 1, 1, '{}', 'same-hash', 1, '1.0', '2026-10-26'),"
                "        (2, 2, 1, '{}', 'same-hash', 1, '1.0', '2026-10-26');"
                "INSERT INTO review (id, plan_version_id, round, report_json, report_sha256,"
                " status, reviewer_mode, created_at)"
                " VALUES (1, 1, 1, '{}', 'r1', 'passed', 'native', '2026-10-26'),"
                "        (2, 2, 1, '{}', 'r2', 'passed', 'native', '2026-10-26');"
                "INSERT INTO override (id, finding_id, teacher_id, reason, approved_at, plan_hash)"
                " VALUES (1, 'F1', 1, '理由足够长的说明', '2026-10-26', 'same-hash'),"
                "        (2, 'F2', 2, '理由足够长的说明', '2026-10-26', 'same-hash');"
            )
            initialize(conn)
            self.assertEqual(current_version(conn), SCHEMA_VERSION)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM plan_version").fetchone()[0], 2)
            rows = dict(conn.execute("SELECT teacher_id, review_id FROM override").fetchall())
            self.assertEqual(rows, {1: 1, 2: 2})
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            conn.close()

    def test_task_board_columns_migrated(self) -> None:
        _, plan, _ = self._seed()
        columns = [row[1] for row in self.conn.execute("PRAGMA table_info(task)")]
        for column in ("quadrant", "board_position", "board_version", "discarded_at"):
            self.assertIn(column, columns)
        row = self.conn.execute("SELECT quadrant, board_position, board_version FROM task LIMIT 1").fetchone()
        if row is not None:
            self.assertEqual(row[0], "important_not_urgent")
            self.assertEqual(int(row[1]), 0)
            self.assertEqual(int(row[2]), 0)
        indexes = [item[1] for item in self.conn.execute("PRAGMA index_list(task)")]
        self.assertIn("idx_task_board", indexes)

    def test_plan_version_idempotency_key_is_unique(self) -> None:
        _, plan, _ = self._seed()
        self.conn.execute(
            "INSERT INTO plan_version (plan_id, version_no, content_json, plan_hash, report_sha256,"
            " schema_version, rubric_version, created_at)"
            " VALUES (?, 2, '{}', 'hash', 'report-1', 1, '1.0', ?)",
            (plan, clock.now_iso()),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO plan_version (plan_id, version_no, content_json, plan_hash, report_sha256,"
                " schema_version, rubric_version, created_at)"
                " VALUES (?, 3, '{}', 'hash', 'report-1', 1, '1.0', ?)",
                (plan, clock.now_iso()),
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
