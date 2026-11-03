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

# 0013 之前：task 已有看板列与正确唯一键，但 quadrant 没有白名单 CHECK
LEGACY_TASK_NO_QUADRANT_CHECK_SQL = """
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
    assignee_id INTEGER REFERENCES user (id),
    group_name TEXT NOT NULL DEFAULT '',
    term TEXT NOT NULL DEFAULT '',
    quadrant TEXT NOT NULL DEFAULT 'important_not_urgent',
    board_position INTEGER NOT NULL DEFAULT 0,
    board_version INTEGER NOT NULL DEFAULT 0,
    discarded_at TEXT,
    UNIQUE (course, week, session, class_name, title)
);
"""

# 更早的基线（#21 之前）：plan_version 既没有 report_sha256，也没有 engine_version
LEGACY_PLAN_VERSION_SQL = """
DROP TABLE plan_version;
CREATE TABLE plan_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES plan (id),
    version_no INTEGER NOT NULL,
    content_json TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    rubric_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (plan_id, version_no)
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
        conn.executescript(LEGACY_PLAN_VERSION_SQL)
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

    def test_repair_rebuilds_override_and_indexes(self) -> None:
        # P1-1/P1-2：v1 的 override 要按 review_id 重建；旧的两列 export 索引要升级为三列部分索引
        conn = self._legacy_db()
        try:
            conn.executescript(
                "DROP TABLE override;"
                "CREATE TABLE override ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " finding_id TEXT NOT NULL UNIQUE,"
                " teacher_id INTEGER REFERENCES user (id),"
                " reason TEXT NOT NULL,"
                " approved_at TEXT NOT NULL,"
                " plan_hash TEXT NOT NULL);"
                "INSERT INTO override (finding_id, teacher_id, reason, approved_at, plan_hash)"
                " VALUES ('F1', 1, '理由足够长的说明', '2026-10-26', 'hash-1');"
                "CREATE UNIQUE INDEX ux_export_job_succeeded"
                " ON export_job (plan_version_id, engine_version) WHERE status = 'succeeded';"
            )
            repair.repair(conn)
            columns = [row[1] for row in conn.execute("PRAGMA table_info(override)")]
            self.assertIn("review_id", columns)
            ddl = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'override'").fetchone()[0]
            self.assertIn("UNIQUE (review_id, finding_id)", ddl)
            # 写入语句必须能编译（ON CONFLICT 目标存在）
            conn.execute(
                "EXPLAIN INSERT INTO override (review_id, finding_id, teacher_id, reason,"
                " approved_at, plan_hash) VALUES (1, 'F1', 1, 'reason long enough',"
                " '2026-10-26', 'hash-1')"
                " ON CONFLICT (review_id, finding_id) DO UPDATE SET reason = excluded.reason"
            )
            export_ddl = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name = 'ux_export_job_succeeded'"
            ).fetchone()[0]
            self.assertIn("report_sha256", export_ddl)
            info = [row[2] for row in conn.execute("PRAGMA index_info(ux_export_job_succeeded)")]
            self.assertEqual(info, ["plan_version_id", "engine_version", "report_sha256"])
            plan_ddl = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name = 'ux_plan_version_report'"
            ).fetchone()[0]
            self.assertIn("WHERE report_sha256 <> ''", plan_ddl)
            self.assertFalse(repair.inspect(conn)["needs_repair"])
        finally:
            conn.close()

    def test_repair_handles_missing_override_and_duplicate_jobs(self) -> None:
        # 缺 override 表要能建出来；重复 succeeded 要先标 failed 再建唯一索引（与 0005 一致）
        conn = sqlite3.connect(":memory:", isolation_level=None)
        try:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.executescript("DROP TABLE override;")
            conn.executescript(SEED_SQL)
            conn.executescript(
                "INSERT INTO export_job (plan_version_id, engine_version, status, operator_id, created_at)"
                " VALUES (1, '1.0.0', 'succeeded', 1, '2026-10-26'),"
                "        (1, '1.0.0', 'succeeded', 1, '2026-10-26');"
            )
            self.assertIn("override", repair.inspect(conn)["missing_tables"])
            repair.repair(conn)
            statuses = [row[0] for row in conn.execute("SELECT status FROM export_job ORDER BY id")]
            self.assertEqual(statuses, ["failed", "succeeded"])
            columns = [row[1] for row in conn.execute("PRAGMA table_info(override)")]
            self.assertIn("review_id", columns)
            self.assertFalse(repair.inspect(conn)["needs_repair"])
        finally:
            conn.close()

    def test_repair_adds_quadrant_check_and_normalizes(self) -> None:
        # R4-04：早期 repair 建的 task 表没有 quadrant CHECK，脏值会让列表/看板 500
        conn = sqlite3.connect(":memory:", isolation_level=None)
        try:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.executescript(LEGACY_TASK_NO_QUADRANT_CHECK_SQL)
            conn.executescript(SEED_SQL)
            conn.execute("UPDATE task SET quadrant = 'legacy_quadrant'")
            state = repair.inspect(conn)
            self.assertFalse(state["task_quadrant_ok"])
            log = repair.repair(conn)
            self.assertTrue(log["rebuilt_task"])
            self.assertTrue(repair.inspect(conn)["task_quadrant_ok"])
            self.assertEqual(conn.execute("SELECT quadrant FROM task").fetchone()[0], "important_not_urgent")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE task SET quadrant = 'legacy_quadrant'")
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

    def test_repair_fixes_duplicate_column_state(self) -> None:
        """迁移跑了一半（列已加、版本没推进）时，initialize 会报 duplicate column，repair 要能救回来。"""
        conn = self._legacy_db()
        try:
            conn.execute("ALTER TABLE plan_version ADD COLUMN report_sha256 TEXT NOT NULL DEFAULT ''")
            conn.execute("PRAGMA user_version=1")
            with self.assertRaises(sqlite3.OperationalError):
                initialize(conn)  # 0002 再次 ADD COLUMN → duplicate column name
            log = repair.repair(conn)
            self.assertIn("plan_version.engine_version", log["added_columns"])
            state = repair.inspect(conn)
            self.assertEqual(state["version"], SCHEMA_VERSION)
            self.assertFalse(state["needs_repair"])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM plan_version").fetchone()[0], 1)
        finally:
            conn.close()
