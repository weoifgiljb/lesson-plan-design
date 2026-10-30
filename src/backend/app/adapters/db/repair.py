# -*- coding: utf-8 -*-
"""数据库结构修复：把早期谱系的库对齐到当前 SCHEMA_VERSION。

背景：迁移器只按 `user_version` 往前走。若库是在早期分支上创建的
（例如 fe-02 的 `SCHEMA_VERSION=2`，只做了任务表重建），版本号会跳过
`0002`–`0010`，导致 `plan_version.report_sha256`、`sample.score` 等列永久缺失，
后续导入/导出直接报 `no such column`。

本模块做三件事，且可重复执行：
1. 补齐缺失列与索引（全部是静态 SQL，不做字符串拼接）；
2. 若 `task` 唯一键不是当前口径 `(course, week, session, class_name, title)`，按 12 步法重建；
3. 回填 `plan_version.report_sha256`、`task.group_name`、`sync_event`，最后写 `user_version`。

回填 `plan_version` 需要临时摘掉"不可更新"触发器（与迁移 0002 同因），
整篇用事务包住，失败即回滚，调用方负责先备份数据库文件。
"""
from __future__ import annotations

import re
import sqlite3
from typing import Any

from app.adapters.db.connection import SCHEMA_VERSION, current_version, set_version

TASK_KEY_COLUMNS = ("course", "week", "session", "class_name", "title")

# 迁移 0003 才建的表：修复脚本自己补齐，未跑过 initialize() 也能对齐
REQUIRED_TABLES = ("sync_event", "override")

CREATE_TABLE_SQL: dict[str, str] = {
    "override": (
        "CREATE TABLE IF NOT EXISTS override ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " review_id INTEGER NOT NULL REFERENCES review (id),"
        " finding_id TEXT NOT NULL,"
        " teacher_id INTEGER REFERENCES user (id),"
        " reason TEXT NOT NULL,"
        " approved_at TEXT NOT NULL,"
        " plan_hash TEXT NOT NULL,"
        " UNIQUE (review_id, finding_id)"
        ")"
    ),
    "sync_event": (
        "CREATE TABLE IF NOT EXISTS sync_event ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " kind TEXT NOT NULL CHECK (kind IN ('version', 'deleted')),"
        " plan_id INTEGER NOT NULL REFERENCES plan (id),"
        " plan_version_id INTEGER REFERENCES plan_version (id),"
        " created_at TEXT NOT NULL"
        ")"
    ),
}

# 静态 DDL：列名与类型写死，避免运行时拼 SQL（BSEC-02）
ADD_COLUMN_SQL: dict[tuple[str, str], str] = {
    ("plan_version", "report_sha256"): (
        "ALTER TABLE plan_version ADD COLUMN report_sha256 TEXT NOT NULL DEFAULT ''"
    ),
    ("user", "group_name"): "ALTER TABLE user ADD COLUMN group_name TEXT NOT NULL DEFAULT ''",
    ("plan_version", "engine_version"): (
        "ALTER TABLE plan_version ADD COLUMN engine_version TEXT NOT NULL DEFAULT ''"
    ),
    ("task", "assignee_id"): "ALTER TABLE task ADD COLUMN assignee_id INTEGER REFERENCES user (id)",
    ("task", "group_name"): "ALTER TABLE task ADD COLUMN group_name TEXT NOT NULL DEFAULT ''",
    ("task", "term"): "ALTER TABLE task ADD COLUMN term TEXT NOT NULL DEFAULT ''",
    ("export_job", "report_sha256"): (
        "ALTER TABLE export_job ADD COLUMN report_sha256 TEXT NOT NULL DEFAULT ''"
    ),
    ("sample", "score"): "ALTER TABLE sample ADD COLUMN score INTEGER NOT NULL DEFAULT 0",
    ("sample", "engine_version"): (
        "ALTER TABLE sample ADD COLUMN engine_version TEXT NOT NULL DEFAULT ''"
    ),
    ("sample", "rule_version"): (
        "ALTER TABLE sample ADD COLUMN rule_version TEXT NOT NULL DEFAULT ''"
    ),
}

CREATE_INDEX_SQL: dict[str, str] = {
    "ux_plan_version_report": (
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_plan_version_report"
        " ON plan_version (plan_id, plan_hash, report_sha256)"
        " WHERE report_sha256 <> ''"
    ),
    "ux_export_job_succeeded": (
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_export_job_succeeded"
        " ON export_job (plan_version_id, engine_version, report_sha256)"
        " WHERE status = 'succeeded'"
    ),
    "idx_audit_created": "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log (created_at)",
    "idx_audit_target": (
        "CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_log (target_type, target_id)"
    ),
    "idx_sync_event_plan": (
        "CREATE INDEX IF NOT EXISTS idx_sync_event_plan ON sync_event (plan_id, id)"
    ),
    "idx_task_assignee": (
        "CREATE INDEX IF NOT EXISTS idx_task_assignee ON task (assignee_id, status)"
    ),
    "idx_task_group": "CREATE INDEX IF NOT EXISTS idx_task_group ON task (group_name, status)",
    "idx_task_identity": (
        "CREATE INDEX IF NOT EXISTS idx_task_identity"
        " ON task (course, week, session, class_name, title)"
    ),
}

INDEX_SPECS: dict[str, tuple[tuple[str, ...], bool]] = {
    # 索引名 -> (期望列, 是否要求部分索引 WHERE)
    "ux_plan_version_report": (("plan_id", "plan_hash", "report_sha256"), True),
    "ux_export_job_succeeded": (("plan_version_id", "engine_version", "report_sha256"), True),
}

DROP_INDEX_SQL: dict[str, str] = {
    "ux_plan_version_report": "DROP INDEX IF EXISTS ux_plan_version_report",
    "ux_export_job_succeeded": "DROP INDEX IF EXISTS ux_export_job_succeeded",
}

INDEX_INFO_SQL: dict[str, str] = {
    "ux_plan_version_report": "PRAGMA index_info(ux_plan_version_report)",
    "ux_export_job_succeeded": "PRAGMA index_info(ux_export_job_succeeded)",
}

OVERRIDE_TABLE_SQL = (
    "CREATE TABLE override_rebuilt ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " review_id INTEGER NOT NULL REFERENCES review (id),"
    " finding_id TEXT NOT NULL,"
    " teacher_id INTEGER REFERENCES user (id),"
    " reason TEXT NOT NULL,"
    " approved_at TEXT NOT NULL,"
    " plan_hash TEXT NOT NULL,"
    " UNIQUE (review_id, finding_id)"
    ")"
)

OVERRIDE_COPY_SQL = (
    "INSERT INTO override_rebuilt (id, review_id, finding_id, teacher_id, reason, approved_at, plan_hash)"
    " SELECT o.id, COALESCE("
    "   (SELECT MIN(r.id) FROM review r"
    "      JOIN plan_version pv ON pv.id = r.plan_version_id"
    "      JOIN plan p ON p.id = pv.plan_id"
    "     WHERE pv.plan_hash = o.plan_hash AND (o.teacher_id IS NULL OR p.owner_id = o.teacher_id)),"
    "   (SELECT MIN(r.id) FROM review r"
    "      JOIN plan_version pv ON pv.id = r.plan_version_id"
    "     WHERE pv.plan_hash = o.plan_hash))"
    " , o.finding_id, o.teacher_id, o.reason, o.approved_at, o.plan_hash"
    " FROM override o"
    " WHERE EXISTS (SELECT 1 FROM review r JOIN plan_version pv ON pv.id = r.plan_version_id"
    "   WHERE pv.plan_hash = o.plan_hash)"
)

OVERRIDE_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_override_review ON override (review_id)"

DEDUPE_EXPORT_SUCCEEDED_SQL = (
    "UPDATE export_job SET status = 'failed'"
    " WHERE status = 'succeeded' AND id NOT IN ("
    "   SELECT MAX(id) FROM export_job WHERE status = 'succeeded'"
    "   GROUP BY plan_version_id, engine_version, report_sha256)"
)

TASK_TABLE_SQL = (
    "CREATE TABLE task_rebuilt ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " course TEXT NOT NULL,"
    " week INTEGER NOT NULL,"
    " session INTEGER NOT NULL,"
    " title TEXT NOT NULL,"
    " class_name TEXT NOT NULL DEFAULT '',"
    " owner_id INTEGER NOT NULL REFERENCES user (id),"
    " due_date TEXT,"
    " status TEXT NOT NULL DEFAULT 'draft'"
    " CHECK (status IN ('draft', 'reviewing', 'passed', 'exported')),"
    " created_at TEXT NOT NULL,"
    " assignee_id INTEGER REFERENCES user (id),"
    " group_name TEXT NOT NULL DEFAULT '',"
    " term TEXT NOT NULL DEFAULT '',"
    " UNIQUE (course, week, session, class_name, title)"
    ")"
)

TASK_COPY_SQL = (
    "INSERT INTO task_rebuilt (id, course, week, session, title, class_name, owner_id,"
    " due_date, status, created_at, assignee_id, group_name, term)"
    " SELECT id, course, week, session, title, class_name, owner_id,"
    " due_date, status, created_at, assignee_id, group_name, term FROM task"
)

BACKFILL_PLAN_VERSION_SQL = (
    "UPDATE plan_version SET report_sha256 = COALESCE("
    " (SELECT r.report_sha256 FROM review r WHERE r.plan_version_id = plan_version.id"
    "  ORDER BY r.round LIMIT 1), '')"
    " WHERE report_sha256 = ''"
)

BACKFILL_SYNC_VERSION_SQL = (
    "INSERT INTO sync_event (kind, plan_id, plan_version_id, created_at)"
    " SELECT 'version', pv.plan_id, pv.id, pv.created_at FROM plan_version pv"
    " WHERE NOT EXISTS (SELECT 1 FROM sync_event e WHERE e.plan_version_id = pv.id)"
)

BACKFILL_SYNC_DELETED_SQL = (
    "INSERT INTO sync_event (kind, plan_id, plan_version_id, created_at)"
    " SELECT 'deleted', p.id, NULL, p.deleted_at FROM plan p"
    " WHERE p.deleted_at IS NOT NULL AND NOT EXISTS ("
    "   SELECT 1 FROM sync_event e WHERE e.plan_id = p.id AND e.kind = 'deleted')"
)

TASK_TRIGGER_PLAN_VERSION_SQL = (
    "CREATE TRIGGER plan_version_no_update BEFORE UPDATE ON plan_version"
    " BEGIN SELECT RAISE(ABORT, 'plan_version is immutable'); END"
)

BACKFILL_TASK_GROUP_SQL = (
    "UPDATE task SET group_name = COALESCE("
    " (SELECT u.group_name FROM user u WHERE u.id = task.owner_id), '')"
    " WHERE group_name = ''"
)


TABLE_INFO_SQL: dict[str, str] = {
    "user": "PRAGMA table_info(user)",
    "plan_version": "PRAGMA table_info(plan_version)",
    "task": "PRAGMA table_info(task)",
    "export_job": "PRAGMA table_info(export_job)",
    "sample": "PRAGMA table_info(sample)",
    "override": "PRAGMA table_info(override)",
}

TASK_DDL_SQL = "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'task'"
UNIQUE_RE = re.compile(r"UNIQUE\s*\(([^)]*)\)", re.I)


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    sql = TABLE_INFO_SQL.get(table)
    if sql is None:
        return set()
    return {str(row[1]) for row in conn.execute(sql).fetchall()}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def _index_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def _task_key(conn: sqlite3.Connection) -> tuple[str, ...]:
    """从建表语句里读出 task 的唯一键列（表级 UNIQUE 不会出现在 sqlite_master 的 index 里）。"""
    row = conn.execute(TASK_DDL_SQL).fetchone()
    if row is None or not row[0]:
        return ()
    match = UNIQUE_RE.search(str(row[0]))
    if match is None:
        return ()
    return tuple(part.strip() for part in match.group(1).split(","))


def inspect(conn: sqlite3.Connection) -> dict[str, Any]:
    """只读检查：返回缺失项与任务键状态，供 CLI 打印和测试断言。"""
    missing_columns: list[str] = []
    for table, column in ADD_COLUMN_SQL:
        if _table_exists(conn, table) and column not in _columns(conn, table):
            missing_columns.append(f"{table}.{column}")
    # 表还不存在时（如 0003 才会建的 sync_event）索引无从创建，单列为 missing_tables
    missing_tables = [
        table for table in REQUIRED_TABLES if not _table_exists(conn, table)
    ]
    missing_indexes = [
        name
        for name, sql in CREATE_INDEX_SQL.items()
        if _table_exists(conn, _table_of(sql)) and not _index_ok(conn, name)
    ]
    key = _task_key(conn) if _table_exists(conn, "task") else ()
    return {
        "version": current_version(conn),
        "target_version": SCHEMA_VERSION,
        "missing_columns": missing_columns,
        "missing_tables": missing_tables,
        "missing_indexes": missing_indexes,
        "task_key": key,
        "task_key_ok": key == TASK_KEY_COLUMNS,
        "override_ok": _override_ok(conn),
        "needs_repair": bool(
            missing_columns
            or missing_tables
            or missing_indexes
            or (key and not key == TASK_KEY_COLUMNS)
            or not _override_ok(conn)
            or current_version(conn) != SCHEMA_VERSION
        ),
    }


def repair(conn: sqlite3.Connection) -> dict[str, Any]:
    """执行修复；调用方负责先备份。返回步骤日志。"""
    log: dict[str, Any] = {
        "added_columns": [],
        "rebuilt_task": False,
        "rebuilt_override": False,
        "notes": [],
    }
    database = conn.execute("PRAGMA database_list").fetchone()[2]

    if conn.in_transaction:
        # 上一次失败的 initialize() 可能留下未结束的事务，先清掉再开自己的
        conn.execute("ROLLBACK")
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("BEGIN IMMEDIATE")
    committed = False
    try:
        _create_missing_tables(conn, log)
        _add_missing_columns(conn, log)
        if _table_exists(conn, "task") and _task_key(conn) != TASK_KEY_COLUMNS:
            _rebuild_task(conn)
            log["rebuilt_task"] = True
        if not _override_ok(conn):
            _rebuild_override(conn)
            log["rebuilt_override"] = True
        _backfill(conn)
        _create_missing_indexes(conn)
        _assert_foreign_keys(conn)
        conn.execute("COMMIT")
        committed = True
    finally:
        # 出错时在 finally 里回滚（不用 except，符合 BA-09 的错误边界约束）
        if not committed and conn.in_transaction:
            conn.execute("ROLLBACK")
        conn.execute("PRAGMA foreign_keys = ON")
    set_version(conn, SCHEMA_VERSION)
    log["db"] = database
    log["version"] = SCHEMA_VERSION
    return log


def _create_missing_tables(conn: sqlite3.Connection, log: dict[str, Any]) -> None:
    for table in REQUIRED_TABLES:
        if not _table_exists(conn, table):
            conn.execute(CREATE_TABLE_SQL[table])
            log["notes"].append(f"created {table}")


def _add_missing_columns(conn: sqlite3.Connection, log: dict[str, Any]) -> None:
    for table, column in ADD_COLUMN_SQL:
        if not _table_exists(conn, table) or column in _columns(conn, table):
            continue
        conn.execute(ADD_COLUMN_SQL[(table, column)])
        log["added_columns"].append(f"{table}.{column}")


def _rebuild_task(conn: sqlite3.Connection) -> None:
    """按 12 步法重建 task 表：唯一键换成当前口径，历史列原样保留。"""
    conn.execute("DROP TABLE IF EXISTS task_rebuilt")
    conn.execute(TASK_TABLE_SQL)
    conn.execute(TASK_COPY_SQL)
    conn.execute("DROP TABLE task")
    conn.execute("ALTER TABLE task_rebuilt RENAME TO task")


def _index_ok(conn: sqlite3.Connection, name: str) -> bool:
    if not _index_exists(conn, name):
        return False
    spec = INDEX_SPECS.get(name)
    if spec is None:
        return True
    expected, need_partial = spec
    rows = conn.execute(INDEX_INFO_SQL[name]).fetchall()
    columns = tuple(str(row[2]) for row in rows)
    if columns != expected:
        return False
    if need_partial:
        ddl = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)
        ).fetchone()
        if ddl is None or "WHERE" not in str(ddl[0]).upper():
            return False
    return True


def _override_ok(conn: sqlite3.Connection) -> bool:
    if not _table_exists(conn, "override"):
        return False
    if "review_id" not in _columns(conn, "override"):
        return False
    ddl = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'override'"
    ).fetchone()
    return ddl is not None and "UNIQUE (review_id, finding_id)" in str(ddl[0])


def _rebuild_override(conn: sqlite3.Connection) -> None:
    """v1 的 override 只有 finding_id 全局唯一；按 review_id 重建并保留可用行。"""
    conn.execute("DROP TABLE IF EXISTS override_rebuilt")
    conn.execute(OVERRIDE_TABLE_SQL)
    if _table_exists(conn, "override"):
        conn.execute(OVERRIDE_COPY_SQL)
        conn.execute("DROP TABLE override")
    conn.execute("ALTER TABLE override_rebuilt RENAME TO override")
    conn.execute(OVERRIDE_INDEX_SQL)


def _backfill(conn: sqlite3.Connection) -> None:
    _backfill_plan_version(conn)
    if "group_name" in _columns(conn, "task"):
        conn.execute(BACKFILL_TASK_GROUP_SQL)
    if _table_exists(conn, "sync_event"):
        conn.execute(BACKFILL_SYNC_VERSION_SQL)
        conn.execute(BACKFILL_SYNC_DELETED_SQL)


def _backfill_plan_version(conn: sqlite3.Connection) -> None:
    # plan_version 有"不可更新"触发器：回填前临时摘掉，回填后原样重建
    has_trigger = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'trigger' AND name = 'plan_version_no_update'"
    ).fetchone()
    if has_trigger is not None:
        conn.execute("DROP TRIGGER plan_version_no_update")
    conn.execute(BACKFILL_PLAN_VERSION_SQL)
    if has_trigger is not None:
        conn.execute(TASK_TRIGGER_PLAN_VERSION_SQL)


def _create_missing_indexes(conn: sqlite3.Connection) -> None:
    for name, sql in CREATE_INDEX_SQL.items():
        if not _table_exists(conn, _table_of(sql)):
            continue
        if _index_ok(conn, name):
            continue
        if _index_exists(conn, name):
            conn.execute(DROP_INDEX_SQL[name])
        if name == "ux_export_job_succeeded":
            conn.execute(DEDUPE_EXPORT_SUCCEEDED_SQL)
        conn.execute(sql)


def _assert_foreign_keys(conn: sqlite3.Connection) -> None:
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"外键检查未通过：{violations[:5]}")


def _table_of(create_sql: str) -> str:
    return create_sql.split(" ON ", 1)[1].split(" (", 1)[0].strip()
