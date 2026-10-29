# -*- coding: utf-8 -*-
"""SQLite 仓储：全后端唯一写 SQL 的地方，也是唯一允许捕获数据库异常的地方。"""
from __future__ import annotations

import contextlib
import json
import sqlite3
import threading
import time
from typing import Any, Callable, Iterator

from app.adapters import clock
from app.domain import task_rules
from app.domain.errors import AppError


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


PLAN_FILTER_KEYS = ("course", "week", "class", "teacher", "created_from", "created_before")


def _has_plan_filters(filters: dict[str, Any] | None) -> bool:
    if not filters:
        return False
    return any(filters.get(key) not in (None, "") for key in PLAN_FILTER_KEYS)


class Repo:
    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock | None = None) -> None:
        self.conn = conn
        self.lock = lock

    def close(self) -> None:
        self.conn.close()

    # ---------- 事务 ----------
    @contextlib.contextmanager
    def transaction(
        self, on_rollback: Callable[[BaseException], None] | None = None
    ) -> Iterator["Repo"]:
        if self.lock is not None:
            self.lock.acquire()
        try:
            self._begin()
            try:
                yield self
                self.conn.execute("COMMIT")
            except BaseException as exc:
                self.conn.execute("ROLLBACK")
                if on_rollback is not None:
                    # 事务已回滚，调用方在此处补写"被回滚的拒绝"审计（在事务外）
                    on_rollback(exc)
                raise
        finally:
            if self.lock is not None:
                self.lock.release()

    def _begin(self) -> None:
        attempt = 0
        while attempt < 3 and not self._try_begin():
            attempt += 1
            time.sleep(0.05 * attempt)
        if attempt >= 3:
            raise AppError("CONFLICT_STALE", "数据库繁忙，请重试")

    def _try_begin(self) -> bool:
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            return True
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            return False

    def health(self) -> str:
        try:
            self.conn.execute("SELECT 1").fetchone()
            return "ok"
        except sqlite3.Error:
            return "down"

    # ---------- 用户与会话 ----------
    def user_by_username(self, username: str) -> dict[str, Any] | None:
        return _row(self.conn.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone())

    def user_by_id(self, user_id: int) -> dict[str, Any] | None:
        return _row(self.conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone())

    def user_by_display_name(self, display_name: str) -> dict[str, Any] | None:
        return _row(
            self.conn.execute("SELECT * FROM user WHERE display_name = ? AND active = 1", (display_name,)).fetchone()
        )

    def insert_user(
        self, username: str, display_name: str, role: str, password_hash: str, group_name: str = ""
    ) -> int:
        cursor = self.conn.execute(
            "INSERT INTO user (username, display_name, group_name, role, password_hash, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (username, display_name, group_name, role, password_hash, clock.now_iso()),
        )
        return int(cursor.lastrowid or 0)

    def set_password(self, user_id: int, password_hash: str) -> None:
        self.conn.execute("UPDATE user SET password_hash = ? WHERE id = ?", (password_hash, user_id))

    def set_login_identity(self, user_id: int, role: str, display_name: str) -> None:
        """建号脚本重置账号时同步角色与姓名：否则"降级管理员"会静默失败（R2-2）。"""
        self.conn.execute(
            "UPDATE user SET role = ?, display_name = ? WHERE id = ?",
            (role, display_name, int(user_id)),
        )

    def bump_login_failure(self, user_id: int, limit: int, locked_until: str | None) -> int:
        """原子自增失败计数，达到上限时同时写入锁定时间，返回自增后的计数。

        不能用"先读 failed_count 再写回"：并发登录时多个请求读到同一个旧值，
        计数会丢更新，5 次失败锁定可被并行请求绕过（第 2 轮评审 R2-1）。
        """
        row = self.conn.execute(
            "UPDATE user SET failed_count = failed_count + 1,"
            " locked_until = CASE WHEN failed_count + 1 >= ? THEN ? ELSE locked_until END"
            " WHERE id = ? RETURNING failed_count",
            (int(limit), locked_until, int(user_id)),
        ).fetchone()
        return int(row["failed_count"]) if row is not None else 0

    def record_login_failure(self, user_id: int, failed_count: int, locked_until: str | None) -> None:
        self.conn.execute(
            "UPDATE user SET failed_count = ?, locked_until = ? WHERE id = ?",
            (failed_count, locked_until, user_id),
        )

    def reset_login_failure(self, user_id: int) -> None:
        self.conn.execute(
            "UPDATE user SET failed_count = 0, locked_until = NULL WHERE id = ?", (user_id,)
        )

    def insert_session(self, user_id: int, token_hash: str, csrf_token: str, expires_at: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO user_session (user_id, token_hash, csrf_token, created_at, expires_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, token_hash, csrf_token, clock.now_iso(), expires_at),
        )
        return int(cursor.lastrowid or 0)

    def session_by_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        return _row(
            self.conn.execute(
                "SELECT * FROM user_session WHERE token_hash = ? AND revoked_at IS NULL", (token_hash,)
            ).fetchone()
        )

    def revoke_session(self, session_id: int) -> None:
        self.conn.execute(
            "UPDATE user_session SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
            (clock.now_iso(), session_id),
        )

    # ---------- 教案与版本 ----------
    def find_plan_by_identity(self, owner_id: int, plan: dict[str, Any]) -> dict[str, Any] | None:
        return _row(
            self.conn.execute(
                "SELECT * FROM plan WHERE owner_id = ? AND course = ? AND week = ? AND session = ?"
                " AND content_title = ? AND deleted_at IS NULL",
                (
                    owner_id,
                    str(plan.get("course") or ""),
                    int(plan.get("week") or 0),
                    int(plan.get("session") or 0),
                    str(plan.get("contentTitle") or ""),
                ),
            ).fetchone()
        )

    def find_or_create_plan(self, owner_id: int, plan: dict[str, Any]) -> int:
        existing = self.find_plan_by_identity(owner_id, plan)
        if existing is not None:
            return int(existing["id"])
        try:
            return self.create_plan(owner_id, plan)
        except sqlite3.IntegrityError as exc:
            raced = self.find_plan_by_identity(owner_id, plan)
            if raced is None:
                raise AppError("CONFLICT_STALE", "教案创建冲突，请重试") from exc
            return int(raced["id"])

    def create_plan(self, owner_id: int, plan: dict[str, Any]) -> int:
        cursor = self.conn.execute(
            "INSERT INTO plan (owner_id, content_title, week, session, course, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                owner_id,
                str(plan.get("contentTitle") or ""),
                int(plan.get("week") or 0),
                int(plan.get("session") or 0),
                str(plan.get("course") or ""),
                clock.now_iso(),
            ),
        )
        return int(cursor.lastrowid or 0)

    def set_current_version(self, plan_id: int, version_id: int) -> None:
        self.conn.execute("UPDATE plan SET current_version_id = ? WHERE id = ?", (version_id, plan_id))

    def count_versions(self, plan_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS total FROM plan_version WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    def version_by_id(self, version_id: int) -> dict[str, Any] | None:
        sql = " ".join(
            (
                "SELECT pv.id AS version_id, pv.plan_id, pv.version_no, pv.plan_hash, pv.content_json,"
                " pv.engine_version, p.content_title, p.owner_id, p.deleted_at,"
                " u.display_name AS teacher, u.group_name AS owner_group,"
                " rv.id AS review_id, rv.round AS review_round, rv.status AS review_status,"
                " rv.report_json, rv.report_sha256",
                "FROM plan_version pv JOIN plan p ON p.id = pv.plan_id JOIN user u ON u.id = p.owner_id",
                self.LATEST_REVIEW_JOIN,
                "WHERE pv.id = ?",
            )
        )
        return _row(self.conn.execute(sql, (version_id,)).fetchone())

    # ---------- 导出 ----------
    def find_export_job(self, version_id: int, engine_version: str) -> dict[str, Any] | None:
        return _row(
            self.conn.execute(
                "SELECT * FROM export_job WHERE plan_version_id = ? AND engine_version = ?"
                " AND status = 'succeeded' ORDER BY id DESC LIMIT 1",
                (version_id, engine_version),
            ).fetchone()
        )

    def create_export_job(
        self, version_id: int, engine_version: str, operator_id: int, status: str,
        docx_path: str = "", docx_sha256: str = "", report_sha256: str = "",
    ) -> int:
        cursor = self.conn.execute(
            "INSERT INTO export_job (plan_version_id, engine_version, report_sha256, status,"
            " docx_path, docx_sha256, operator_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (version_id, engine_version, report_sha256, status, docx_path, docx_sha256,
             operator_id, clock.now_iso()),
        )
        return int(cursor.lastrowid or 0)

    def update_export_job(
        self, job_id: int, status: str, docx_path: str = "", docx_sha256: str = ""
    ) -> bool:
        try:
            self.conn.execute(
                "UPDATE export_job SET status = ?, docx_path = ?, docx_sha256 = ? WHERE id = ?",
                (status, docx_path, docx_sha256, job_id),
            )
        except sqlite3.IntegrityError:
            return False
        return True

    def get_export_job(self, job_id: int) -> dict[str, Any] | None:
        sql = " ".join(
            (
                "SELECT j.*, pv.plan_id, pv.version_no, pv.plan_hash, p.content_title, p.owner_id,"
                " u.display_name AS teacher, u.group_name AS owner_group",
                "FROM export_job j JOIN plan_version pv ON pv.id = j.plan_version_id",
                "JOIN plan p ON p.id = pv.plan_id JOIN user u ON u.id = p.owner_id",
                "WHERE j.id = ?",
            )
        )
        return _row(self.conn.execute(sql, (job_id,)).fetchone())

    # ---------- 样例库 ----------
    def find_sample(self, course: str, week: int, session: int, title: str) -> dict[str, Any] | None:
        return _row(
            self.conn.execute(
                "SELECT * FROM sample WHERE course = ? AND week = ? AND session = ? AND title = ?",
                (course, int(week), int(session), title),
            ).fetchone()
        )

    def insert_sample(
        self,
        course: str,
        week: int,
        session: int,
        title: str,
        json_path: str,
        plan_hash: str,
        *,
        score: int = 0,
        engine_version: str = "",
        rule_version: str = "",
    ) -> int:
        try:
            cursor = self.conn.execute(
                "INSERT INTO sample (course, week, session, title, json_path, plan_hash, valid,"
                " score, engine_version, rule_version) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
                (
                    course, int(week), int(session), title, json_path, plan_hash,
                    int(score), engine_version, rule_version,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise AppError("CONFLICT_STALE", "同一课题的样例已存在") from exc
        return int(cursor.lastrowid or 0)

    def get_sample(self, sample_id: int) -> dict[str, Any] | None:
        return _row(self.conn.execute("SELECT * FROM sample WHERE id = ?", (sample_id,)).fetchone())

    def list_samples(
        self, filters: dict[str, Any], limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        where = ["1 = 1"]
        params: list[Any] = []
        for column, key in (("course", "course"), ("week", "week"), ("session", "session")):
            value = filters.get(key)
            if value not in (None, ""):
                where.append(f"{column} = ?")
                params.append(value)
        if filters.get("q"):
            escaped = str(filters["q"]).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            where.append("title LIKE ? ESCAPE '\\'")
            params.append(f"%{escaped}%")
        condition = " AND ".join(where)
        count_sql = " ".join(("SELECT COUNT(*) AS total FROM sample WHERE", condition))
        count = self.conn.execute(count_sql, params).fetchone()
        rows_sql = " ".join(
            ("SELECT * FROM sample WHERE", condition, "ORDER BY id DESC LIMIT ? OFFSET ?")
        )
        rows = self.conn.execute(rows_sql, (*params, int(limit), int(offset))).fetchall()
        return [dict(row) for row in rows], int(count["total"] if count is not None else 0)

    # ---------- 任务 ----------
    def insert_task(
        self, course: str, week: int, session: int, title: str, class_name: str,
        owner_id: int, due_date: str | None,
    ) -> int:
        try:
            cursor = self.conn.execute(
                "INSERT INTO task (course, week, session, title, class_name, owner_id, due_date, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', ?)",
                (course, int(week), int(session), title, class_name, owner_id, due_date, clock.now_iso()),
            )
        except sqlite3.IntegrityError as exc:
            raise AppError("CONFLICT_STALE", "同一课程/周次/课次/班级的任务已存在") from exc
        return int(cursor.lastrowid or 0)

    def update_task(self, task_id: int, *, title: str, due_date: str | None) -> None:
        self.conn.execute(
            "UPDATE task SET title = ?, due_date = ? WHERE id = ?", (title, due_date, int(task_id))
        )

    def set_task_status(self, task_id: int, status: str) -> None:
        self.conn.execute("UPDATE task SET status = ? WHERE id = ?", (status, int(task_id)))

    def find_task(
        self, course: str, week: int, session: int, class_name: str
    ) -> dict[str, Any] | None:
        return _row(
            self.conn.execute(
                "SELECT * FROM task WHERE course = ? AND week = ? AND session = ? AND class_name = ?",
                (course, int(week), int(session), class_name),
            ).fetchone()
        )

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        return _row(
            self.conn.execute(
                "SELECT t.*, u.display_name AS teacher, u.group_name AS owner_group"
                " FROM task t JOIN user u ON u.id = t.owner_id WHERE t.id = ?",
                (task_id,),
            ).fetchone()
        )

    def list_tasks(
        self, scope: dict[str, Any], filters: dict[str, Any], limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        condition, params = self._scope_condition(scope, "t.owner_id")
        extra, more = self._task_where(filters)
        where = " AND ".join([condition, extra])
        joins = (
            " FROM task t JOIN user u ON u.id = t.owner_id"
        )
        count = self.conn.execute(
            " ".join(("SELECT COUNT(*) AS total", joins, "WHERE", where)), (*params, *more)
        ).fetchone()
        rows = self.conn.execute(
            " ".join(
                (
                    "SELECT t.*, u.display_name AS teacher, u.group_name AS owner_group",
                    joins,
                    "WHERE",
                    where,
                    "ORDER BY (t.due_date IS NULL), t.due_date ASC, t.id DESC LIMIT ? OFFSET ?",
                )
            ),
            (*params, *more, int(limit), int(offset)),
        ).fetchall()
        return [dict(row) for row in rows], int(count["total"] if count is not None else 0)

    def _task_where(self, filters: dict[str, Any]) -> tuple[str, list[Any]]:
        where = ["1 = 1"]
        params: list[Any] = []
        for column, key in (("t.course", "course"), ("t.week", "week"), ("t.status", "status")):
            value = filters.get(key)
            if value not in (None, ""):
                where.append(f"{column} = ?")
                params.append(value)
        return " AND ".join(where), params

    def attach_task_for_plan(
        self, plan_id: int, plan: dict[str, Any], status: str, task_id: int | None = None
    ) -> int | None:
        owner = self.conn.execute("SELECT owner_id FROM plan WHERE id = ?", (plan_id,)).fetchone()
        if owner is None:
            return None
        if task_id is not None:
            # 显式 taskId 优先：直接绑定并校验归属
            task = _row(self.conn.execute("SELECT * FROM task WHERE id = ?", (int(task_id),)).fetchone())
            if task is None or int(task["owner_id"]) != int(owner["owner_id"]):
                return None
        else:
            # 启发式匹配：把班级纳入条件；命中 0 条或跨班多条都不静默挑一条
            class_name = str(plan.get("className") or plan.get("class") or "")
            params: list[Any] = [
                int(owner["owner_id"]),
                str(plan.get("course") or ""),
                int(plan.get("week") or 0),
                int(plan.get("session") or 0),
                str(plan.get("contentTitle") or ""),
            ]
            if class_name:
                sql = (
                    "SELECT * FROM task WHERE owner_id = ? AND course = ? AND week = ? AND session = ?"
                    " AND title = ? AND class_name = ? ORDER BY id LIMIT 2"
                )
                params.append(class_name)
            else:
                sql = (
                    "SELECT * FROM task WHERE owner_id = ? AND course = ? AND week = ? AND session = ?"
                    " AND title = ? ORDER BY id LIMIT 2"
                )
            rows = self.conn.execute(sql, params).fetchall()
            if len(rows) != 1:
                return None
            task = dict(rows[0])
        self.conn.execute("UPDATE plan SET task_id = ? WHERE id = ? AND task_id IS NULL", (task["id"], plan_id))
        if task_rules.TASK_RANK.get(status, 0) > task_rules.TASK_RANK.get(str(task["status"]), 0):
            self.conn.execute("UPDATE task SET status = ? WHERE id = ?", (status, task["id"]))
            return int(task["id"])
        return None

    def task_for_plan(self, plan_id: int) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT task_id FROM plan WHERE id = ?", (plan_id,)).fetchone()
        if row is None or row["task_id"] is None:
            return None
        return self.get_task(int(row["task_id"]))

    def mark_task_exported(self, plan_id: int) -> int | None:
        row = self.conn.execute("SELECT task_id FROM plan WHERE id = ?", (plan_id,)).fetchone()
        if row is None or row["task_id"] is None:
            return None
        task_id = int(row["task_id"])
        cursor = self.conn.execute(
            "UPDATE task SET status = 'exported' WHERE id = ? AND status != 'exported'", (task_id,)
        )
        return task_id if cursor.rowcount else None

    # ---------- 用户管理 ----------
    def list_users(
        self, filters: dict[str, Any], limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        where = ["1 = 1"]
        params: list[Any] = []
        for column, key in (("role", "role"), ("group_name", "group"), ("active", "active")):
            value = filters.get(key)
            if value not in (None, ""):
                where.append(f"{column} = ?")
                params.append(value)
        if filters.get("q"):
            where.append("(username LIKE ? OR display_name LIKE ?)")
            like = f"%{filters['q']}%"
            params.extend([like, like])
        condition = " AND ".join(where)
        count = self.conn.execute(
            " ".join(("SELECT COUNT(*) AS total FROM user WHERE", condition)), params
        ).fetchone()
        rows = self.conn.execute(
            " ".join(
                (
                    "SELECT id, username, display_name, group_name, role, active,"
                    " must_change_password, created_at FROM user WHERE",
                    condition,
                    "ORDER BY id DESC LIMIT ? OFFSET ?",
                )
            ),
            (*params, int(limit), int(offset)),
        ).fetchall()
        return [dict(row) for row in rows], int(count["total"] if count is not None else 0)

    # ---------- 统计 ----------
    def stats_plans(self, scope: dict[str, Any], filters: dict[str, Any]) -> list[dict[str, Any]]:
        condition, params = self._scope_condition(scope)
        extra, more = self._stats_where(filters)
        where = " AND ".join([condition, "p.deleted_at IS NULL", extra])
        sql = " ".join(
            (
                "SELECT p.id AS plan_id, p.created_at AS plan_created_at, pv.content_json, pv.plan_hash,"
                " pv.version_no, rv.id AS review_id, rv.status AS review_status, rv.round AS review_round,"
                " rv.report_json, rv.report_sha256",
                "FROM plan p JOIN user u ON u.id = p.owner_id",
                "LEFT JOIN plan_version pv ON pv.id = p.current_version_id",
                self.LATEST_REVIEW_JOIN,
                "WHERE",
                where,
            )
        )
        return self._group(sql, (*params, *more))

    def stats_rounds(self, plan_ids: list[int]) -> dict[int, list[int]]:
        if not plan_ids:
            return {}
        placeholders = ",".join("?" for _ in plan_ids)
        sql = " ".join(
            (
                "SELECT pv.plan_id AS plan_id, rv.round AS round FROM review rv",
                "JOIN plan_version pv ON pv.id = rv.plan_version_id",
                f"WHERE pv.plan_id IN ({placeholders}) ORDER BY pv.plan_id, rv.round",
            )
        )
        rows = self.conn.execute(sql, tuple(int(item) for item in plan_ids)).fetchall()
        grouped: dict[int, list[int]] = {}
        for row in rows:
            grouped.setdefault(int(row["plan_id"]), []).append(int(row["round"]))
        return grouped

    def stats_sync(
        self, scope: dict[str, Any], filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        # sync_log 没有教案维度（course/week/teacher）字段：带筛选时明确返回空，
        # 让该指标 available=false，避免"筛选条件被回显、数字却是全量"的假一致。
        if _has_plan_filters(filters):
            return []
        condition, params = self._scope_condition(scope, "s.operator_id")
        return self._group(
            "SELECT s.result AS key, COUNT(*) AS total FROM sync_log s"
            " LEFT JOIN user u ON u.id = s.operator_id"
            f" WHERE {condition} GROUP BY s.result",
            params,
        )

    def stats_tasks(
        self, scope: dict[str, Any], filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        condition, params = self._scope_condition(scope, "t.owner_id")
        extra, more = self._task_where(filters)
        return self._group(
            "SELECT t.status AS key, COUNT(*) AS total FROM task t"
            " LEFT JOIN user u ON u.id = t.owner_id"
            f" WHERE {condition} AND {extra} GROUP BY t.status",
            (*params, *more),
        )

    def stats_exports(
        self, scope: dict[str, Any], filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        condition, params = self._scope_condition(scope)
        extra, more = self._stats_where(dict(filters or {}))
        sql = " ".join(
            (
                "SELECT j.created_at AS export_created_at,"
                " COALESCE(t.created_at, p.created_at) AS start_at",
                "FROM export_job j JOIN plan_version pv ON pv.id = j.plan_version_id",
                "JOIN plan p ON p.id = pv.plan_id LEFT JOIN task t ON t.id = p.task_id",
                "JOIN user u ON u.id = p.owner_id",
                "WHERE j.status = 'succeeded' AND p.deleted_at IS NULL AND",
                condition,
                "AND",
                extra,
            )
        )
        return self._group(sql, (*params, *more))

    def _task_where(self, filters: dict[str, Any] | None) -> tuple[str, list[Any]]:
        where = ["1 = 1"]
        params: list[Any] = []
        data = dict(filters or {})
        for column, key in (("t.course", "course"), ("t.week", "week"), ("t.class_name", "class"), ("u.display_name", "teacher")):
            value = data.get(key)
            if value not in (None, ""):
                where.append(f"{column} = ?")
                params.append(value)
        if data.get("created_from"):
            where.append("t.created_at >= ?")
            params.append(str(data["created_from"]))
        if data.get("created_before"):
            where.append("t.created_at < ?")
            params.append(str(data["created_before"]))
        return " AND ".join(where), params

    def _stats_where(self, filters: dict[str, Any]) -> tuple[str, list[Any]]:
        where = ["1 = 1"]
        params: list[Any] = []
        class_name = filters.get("class")
        if class_name not in (None, ""):
            where.append("p.task_id IN (SELECT id FROM task WHERE class_name = ?)")
            params.append(class_name)
        for column, key in (("p.course", "course"), ("p.week", "week"), ("u.display_name", "teacher")):
            value = filters.get(key)
            if value not in (None, ""):
                where.append(f"{column} = ?")
                params.append(value)
        if filters.get("created_from"):
            where.append("p.created_at >= ?")
            params.append(str(filters["created_from"]))
        if filters.get("created_before"):
            where.append("p.created_at < ?")
            params.append(str(filters["created_before"]))
        return " AND ".join(where), params

    def _scope_condition(
        self, scope: dict[str, Any], owner_column: str = "p.owner_id"
    ) -> tuple[str, list[Any]]:
        owner_id = scope.get("owner_id")
        group_name = scope.get("group_name")
        if owner_id is not None:
            return f"{owner_column} = ?", [int(owner_id)]
        if group_name:
            return "u.group_name = ?", [str(group_name)]
        return "1 = 1", []

    def _group(self, sql: str, params: tuple[Any, ...] | list[Any]) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    # 同一版本可能有多轮审查（schema 允许），列表/详情只取最新一轮，避免 JOIN 放大行数。
    LATEST_REVIEW_JOIN = (
        "LEFT JOIN review rv ON rv.id = ("
        "SELECT rv2.id FROM review rv2 WHERE rv2.plan_version_id = pv.id"
        " ORDER BY rv2.round DESC LIMIT 1)"
    )
    LIBRARY_SELECT = (
        "SELECT p.id AS plan_id, p.content_title, p.course, p.week, p.session, p.owner_id,"
        " p.current_version_id, p.created_at, p.deleted_at,"
        " u.display_name AS teacher, u.group_name AS owner_group,"
        " pv.version_no AS version_no, pv.plan_hash AS plan_hash, pv.engine_version AS engine_version,"
        " pv.created_at AS version_created_at, rv.id AS review_id, rv.status AS review_status,"
        " rv.round AS review_round, rv.reviewer_mode AS reviewer_mode, rv.report_sha256 AS report_sha256"
        " FROM plan p JOIN user u ON u.id = p.owner_id"
        " LEFT JOIN plan_version pv ON pv.id = p.current_version_id"
        " " + LATEST_REVIEW_JOIN
    )

    def list_plans(
        self, scope: dict[str, Any], filters: dict[str, Any], limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        where, params = self._library_where(scope, filters)
        count_sql = " ".join(
            (
                "SELECT COUNT(DISTINCT p.id) AS total FROM plan p JOIN user u ON u.id = p.owner_id",
                "LEFT JOIN plan_version pv ON pv.id = p.current_version_id",
                self.LATEST_REVIEW_JOIN,
                "WHERE",
                where,
            )
        )
        count = self.conn.execute(count_sql, params).fetchone()
        rows_sql = " ".join((self.LIBRARY_SELECT, "WHERE", where, "ORDER BY p.id DESC LIMIT ? OFFSET ?"))
        rows = self.conn.execute(rows_sql, (*params, int(limit), int(offset))).fetchall()
        return [dict(row) for row in rows], int(count["total"] if count is not None else 0)

    def get_plan(self, plan_id: int, *, include_deleted: bool = False) -> dict[str, Any] | None:
        condition = "p.id = ?" if include_deleted else "p.id = ? AND p.deleted_at IS NULL"
        sql = " ".join((self.LIBRARY_SELECT, "WHERE", condition))
        return _row(self.conn.execute(sql, (plan_id,)).fetchone())

    def list_versions(self, plan_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT pv.id AS version_id, pv.version_no, pv.plan_hash, pv.engine_version, pv.created_at,"
            " pv.content_json, rv.round, rv.status, rv.report_sha256, rv.reviewer_mode"
            " FROM plan_version pv LEFT JOIN review rv ON rv.id = ("
            "SELECT rv2.id FROM review rv2 WHERE rv2.plan_version_id = pv.id"
            " ORDER BY rv2.round DESC LIMIT 1)"
            " WHERE pv.plan_id = ? ORDER BY pv.version_no",
            (plan_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def version_by_no(self, plan_id: int, version_no: int) -> dict[str, Any] | None:
        return _row(
            self.conn.execute(
                "SELECT pv.id AS version_id, pv.version_no, pv.plan_hash, pv.content_json, pv.created_at,"
                " rv.round, rv.status, rv.report_sha256"
                " FROM plan_version pv LEFT JOIN review rv ON rv.id = ("
                "SELECT rv2.id FROM review rv2 WHERE rv2.plan_version_id = pv.id"
                " ORDER BY rv2.round DESC LIMIT 1)"
                " WHERE pv.plan_id = ? AND pv.version_no = ?",
                (plan_id, version_no),
            ).fetchone()
        )

    # ---------- 审查中心 ----------
    REVIEW_SELECT = (
        "SELECT rv.id AS review_id, rv.plan_version_id, rv.round, rv.status, rv.reviewer_mode,"
        " rv.report_sha256, rv.created_at, rv.report_json,"
        " pv.version_no, pv.plan_hash, p.id AS plan_id, p.content_title, p.course, p.week, p.session,"
        " p.owner_id, p.deleted_at, u.display_name AS teacher, u.group_name AS owner_group"
        " FROM review rv JOIN plan_version pv ON pv.id = rv.plan_version_id"
        " JOIN plan p ON p.id = pv.plan_id JOIN user u ON u.id = p.owner_id"
    )

    def list_reviews(
        self, scope: dict[str, Any], filters: dict[str, Any], limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        where, params = self._review_where(scope, filters)
        count_sql = " ".join(
            (
                "SELECT COUNT(DISTINCT rv.id) AS total FROM review rv",
                "JOIN plan_version pv ON pv.id = rv.plan_version_id",
                "JOIN plan p ON p.id = pv.plan_id JOIN user u ON u.id = p.owner_id",
                "WHERE",
                where,
            )
        )
        count = self.conn.execute(count_sql, params).fetchone()
        rows_sql = " ".join((self.REVIEW_SELECT, "WHERE", where, "ORDER BY rv.id DESC LIMIT ? OFFSET ?"))
        rows = self.conn.execute(rows_sql, (*params, int(limit), int(offset))).fetchall()
        return [dict(row) for row in rows], int(count["total"] if count is not None else 0)

    def get_review(self, review_id: int) -> dict[str, Any] | None:
        sql = " ".join((self.REVIEW_SELECT, "WHERE rv.id = ?"))
        return _row(self.conn.execute(sql, (review_id,)).fetchone())

    def parse_report(self, text: Any) -> dict[str, Any] | None:
        """解析 report_json：坏数据返回 None，让调用方标红而不是整页 500。"""
        if not isinstance(text, str) or not text:
            return None
        try:
            data = json.loads(text)
        except (TypeError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def plan_rounds(self, plan_id: int) -> list[int]:
        rows = self.conn.execute(
            "SELECT rv.round FROM review rv JOIN plan_version pv ON pv.id = rv.plan_version_id"
            " WHERE pv.plan_id = ? ORDER BY rv.round",
            (plan_id,),
        ).fetchall()
        return [int(row["round"]) for row in rows]

    def plan_rounds_many(self, plan_ids: list[int]) -> dict[int, list[int]]:
        if not plan_ids:
            return {}
        placeholders = ",".join("?" for _ in plan_ids)
        sql = " ".join(
            (
                "SELECT pv.plan_id AS plan_id, rv.round AS round FROM review rv",
                "JOIN plan_version pv ON pv.id = rv.plan_version_id",
                f"WHERE pv.plan_id IN ({placeholders}) ORDER BY pv.plan_id, rv.round",
            )
        )
        rows = self.conn.execute(sql, tuple(int(item) for item in plan_ids)).fetchall()
        grouped: dict[int, list[int]] = {}
        for row in rows:
            grouped.setdefault(int(row["plan_id"]), []).append(int(row["round"]))
        return grouped

    def _review_where(self, scope: dict[str, Any], filters: dict[str, Any]) -> tuple[str, list[Any]]:
        where = ["1 = 1"]
        params: list[Any] = []
        owner_id = scope.get("owner_id")
        group_name = scope.get("group_name")
        if owner_id is not None:
            where.append("p.owner_id = ?")
            params.append(int(owner_id))
        elif group_name:
            where.append("u.group_name = ?")
            params.append(str(group_name))
        for column, key in (("rv.status", "status"), ("u.display_name", "teacher")):
            value = filters.get(key)
            if value not in (None, ""):
                where.append(f"{column} = ?")
                params.append(value)
        severity = filters.get("severity")
        if severity:
            where.append("EXISTS (SELECT 1 FROM finding f WHERE f.review_id = rv.id AND f.severity = ?)")
            params.append(severity)
        if filters.get("created_from"):
            where.append("rv.created_at >= ?")
            params.append(str(filters["created_from"]))
        if filters.get("created_before"):
            where.append("rv.created_at < ?")
            params.append(str(filters["created_before"]))
        return " AND ".join(where), params

    # ---------- 双端同步 ----------
    def plan_head(self, plan_id: int) -> dict[str, Any] | None:
        return _row(
            self.conn.execute(
                "SELECT pv.id AS version_id, pv.version_no, pv.plan_hash, pv.created_at, p.deleted_at"
                " FROM plan_version pv JOIN plan p ON p.id = pv.plan_id"
                " WHERE pv.plan_id = ? AND pv.id = p.current_version_id",
                (plan_id,),
            ).fetchone()
        )

    def pull_events(
        self, scope: dict[str, Any], since: int, limit: int
    ) -> list[dict[str, Any]]:
        """按同步事件游标增量拉取：入库=version、软删除=deleted（删除也能传播）。"""
        where, params = self._pull_where(scope)
        sql = " ".join(
            (
                "SELECT e.id AS event_id, e.kind, e.plan_id, e.plan_version_id, e.created_at AS event_at,"
                " pv.version_no, pv.plan_hash, pv.content_json, pv.created_at,"
                " p.content_title, p.owner_id, p.deleted_at, u.display_name AS teacher",
                "FROM sync_event e JOIN plan p ON p.id = e.plan_id JOIN user u ON u.id = p.owner_id",
                "LEFT JOIN plan_version pv ON pv.id = e.plan_version_id",
                "WHERE e.id > ?",
                where,
                "ORDER BY e.id LIMIT ?",
            )
        )
        rows = self.conn.execute(sql, (int(since), *params, int(limit))).fetchall()
        return [dict(row) for row in rows]

    def pull_versions(
        self, scope: dict[str, Any], since: int, limit: int
    ) -> list[dict[str, Any]]:
        where, params = self._pull_where(scope)
        sql = " ".join(
            (
                "SELECT pv.id AS version_id, pv.plan_id, pv.version_no, pv.plan_hash, pv.content_json,"
                " pv.created_at, p.content_title, p.owner_id, p.deleted_at, u.display_name AS teacher",
                "FROM plan_version pv JOIN plan p ON p.id = pv.plan_id JOIN user u ON u.id = p.owner_id",
                "WHERE pv.id > ?",
                where,
                "ORDER BY pv.id LIMIT ?",
            )
        )
        rows = self.conn.execute(sql, (int(since), *params, int(limit))).fetchall()
        return [dict(row) for row in rows]

    def find_plan_by_identity_scope(
        self, scope: dict[str, Any], plan: dict[str, Any]
    ) -> dict[str, Any] | None:
        where, params = self._pull_where(scope)
        sql = " ".join(
            (
                "SELECT p.* FROM plan p JOIN user u ON u.id = p.owner_id",
                "WHERE p.course = ? AND p.week = ? AND p.session = ? AND p.content_title = ?",
                "AND p.deleted_at IS NULL",
                where,
                "ORDER BY p.id DESC LIMIT 1",
            )
        )
        return _row(
            self.conn.execute(
                sql,
                (
                    str(plan.get("course") or ""),
                    int(plan.get("week") or 0),
                    int(plan.get("session") or 0),
                    str(plan.get("contentTitle") or ""),
                    *params,
                ),
            ).fetchone()
        )

    def insert_sync_log(
        self,
        direction: str,
        package_sha256: str,
        plan_hash: str,
        result: str,
        conflict_code: str,
        operator_id: int | None,
    ) -> int:
        cursor = self.conn.execute(
            "INSERT INTO sync_log (direction, package_sha256, plan_hash, result, conflict_code,"
            " operator_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (direction, package_sha256, plan_hash, result, conflict_code, operator_id, clock.now_iso()),
        )
        return int(cursor.lastrowid or 0)

    def _pull_where(self, scope: dict[str, Any]) -> tuple[str, list[Any]]:
        owner_id = scope.get("owner_id")
        group_name = scope.get("group_name")
        if owner_id is not None:
            return "AND p.owner_id = ?", [int(owner_id)]
        if group_name:
            return "AND u.group_name = ?", [str(group_name)]
        return "", []

    def soft_delete_plan(self, plan_id: int) -> bool:
        cursor = self.conn.execute(
            "UPDATE plan SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (clock.now_iso(), plan_id),
        )
        return bool(cursor.rowcount)

    def _library_where(self, scope: dict[str, Any], filters: dict[str, Any]) -> tuple[str, list[Any]]:
        where = ["p.deleted_at IS NULL"]
        params: list[Any] = []
        owner_id = scope.get("owner_id")
        group_name = scope.get("group_name")
        if owner_id is not None:
            where.append("p.owner_id = ?")
            params.append(int(owner_id))
        elif group_name:
            where.append("u.group_name = ?")
            params.append(str(group_name))
        for column, key in (
            ("p.course", "course"),
            ("p.week", "week"),
            ("p.session", "session"),
            ("rv.status", "status"),
            ("u.display_name", "teacher"),
        ):
            value = filters.get(key)
            if value not in (None, ""):
                where.append(f"{column} = ?")
                params.append(value)
        return " AND ".join(where), params

    def last_round(self, plan_id: int) -> int:
        row = self.conn.execute(
            "SELECT MAX(review.round) AS round FROM review"
            " JOIN plan_version ON plan_version.id = review.plan_version_id"
            " WHERE plan_version.plan_id = ?",
            (plan_id,),
        ).fetchone()
        return int(row["round"] or 0) if row is not None else 0

    def find_version(self, plan_id: int, plan_hash: str, report_sha256: str) -> dict[str, Any] | None:
        return _row(
            self.conn.execute(
                "SELECT plan_version.id AS version_id, plan_version.version_no AS version_no,"
                " plan_version.plan_hash AS plan_hash, review.id AS review_id, plan_version.plan_id AS plan_id"
                " FROM plan_version JOIN review ON review.plan_version_id = plan_version.id"
                " WHERE plan_version.plan_id = ? AND plan_version.plan_hash = ? AND review.report_sha256 = ?"
                " ORDER BY plan_version.version_no DESC LIMIT 1",
                (plan_id, plan_hash, report_sha256),
            ).fetchone()
        )

    def next_version_no(self, plan_id: int) -> int:
        row = self.conn.execute(
            "SELECT MAX(version_no) AS version_no FROM plan_version WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        return int(row["version_no"] or 0) + 1 if row is not None else 1

    def insert_version_or_existing(
        self, plan_id: int, version_no: int, content_json: str, plan_hash: str,
        report_sha256: str, schema_version: int, rubric_version: str, engine_version: str,
    ) -> tuple[int, bool]:
        try:
            cursor = self.conn.execute(
                "INSERT INTO plan_version (plan_id, version_no, content_json, plan_hash, report_sha256,"
                " schema_version, rubric_version, engine_version, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    plan_id, version_no, content_json, plan_hash, report_sha256,
                    schema_version, rubric_version, engine_version, clock.now_iso(),
                ),
            )
            return int(cursor.lastrowid or 0), True
        except sqlite3.IntegrityError as exc:
            # 唯一索引兜底：同一 (plan_id, plan_hash, report_sha256) 只允许一版
            existing = self.conn.execute(
                "SELECT id FROM plan_version WHERE plan_id = ? AND plan_hash = ? AND report_sha256 = ?"
                " ORDER BY version_no DESC LIMIT 1",
                (plan_id, plan_hash, report_sha256),
            ).fetchone()
            if existing is None:
                raise AppError("CONFLICT_STALE", "版本冲突，请重试") from exc
            return int(existing["id"]), False

    def close(self) -> None:
        self.conn.close()
    # ---------- 同步事件 ----------
    def insert_sync_event(self, kind: str, plan_id: int, plan_version_id: int | None = None) -> int:
        """写一条同步事件：version=新增版本、deleted=软删除；pull 用事件 id 作游标。"""
        cursor = self.conn.execute(
            "INSERT INTO sync_event (kind, plan_id, plan_version_id, created_at) VALUES (?, ?, ?, ?)",
            (kind, int(plan_id), None if plan_version_id is None else int(plan_version_id), clock.now_iso()),
        )
        return int(cursor.lastrowid or 0)

    # ---------- 审查 ----------
    def insert_review(
        self, version_id: int, round_number: int, report_json: str, report_sha256: str,
        status: str, reviewer_mode: str,
    ) -> int:
        cursor = self.conn.execute(
            "INSERT INTO review (plan_version_id, round, report_json, report_sha256, status,"
            " reviewer_mode, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (version_id, round_number, report_json, report_sha256, status, reviewer_mode, clock.now_iso()),
        )
        return int(cursor.lastrowid or 0)

    def insert_findings(self, review_id: int, findings: list[dict[str, Any]]) -> None:
        for item in findings:
            self.conn.execute(
                "INSERT INTO finding (review_id, finding_id, severity, status, hypothesis)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    review_id,
                    str(item.get("id") or ""),
                    str(item.get("severity") or "minor"),
                    str(item.get("status") or "open"),
                    str(item.get("hypothesis") or ""),
                ),
            )

    def insert_overrides(self, review_id: int, overrides: list[dict[str, Any]]) -> None:
        for item in overrides:
            teacher = self.user_by_display_name(str(item.get("teacher") or ""))
            if teacher is None:
                # 放行必须能归属到真实教师，否则证据链失效：直接拒收而不是落 NULL
                raise AppError(
                    "REPORT_INCONSISTENT", f"放行记录中的教师不存在：{item.get('teacher') or ''}"
                )
            cursor = self.conn.execute(
                "INSERT INTO override (review_id, finding_id, teacher_id, reason, approved_at, plan_hash)"
                " VALUES (?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (review_id, finding_id) DO UPDATE SET"
                " reason = excluded.reason, approved_at = excluded.approved_at",
                (
                    review_id,
                    str(item.get("findingId") or ""),
                    int(teacher["id"]),
                    str(item.get("reason") or ""),
                    str(item.get("approvedAt") or clock.now_iso()),
                    str(item.get("planHash") or ""),
                ),
            )
            if cursor.rowcount < 0:  # pragma: no cover - 防御
                raise AppError("CONFLICT_STALE", "放行记录写入失败")

    # ---------- 审计 ----------
    def insert_audit(
        self, actor_id: int | None, action: str, target_type: str, target_id: str,
        detail: dict[str, Any] | None = None, ip: str = "", trace_id: str = "",
        before_hash: str = "", after_hash: str = "",
    ) -> None:
        self.conn.execute(
            "INSERT INTO audit_log (actor_id, action, target_type, target_id, before_hash, after_hash,"
            " detail_json, ip, trace_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                actor_id,
                action,
                target_type,
                target_id,
                before_hash,
                after_hash,
                json.dumps(detail or {}, ensure_ascii=False),
                ip,
                trace_id,
                clock.now_iso(),
            ),
        )

    def list_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()
        return [dict(row) for row in rows]

    AUDIT_SELECT = (
        "SELECT a.id, a.actor_id, a.action, a.target_type, a.target_id, a.detail_json,"
        " a.ip, a.trace_id, a.before_hash, a.after_hash, a.created_at,"
        " u.display_name AS actor_name, u.role AS actor_role, u.group_name AS actor_group"
        " FROM audit_log a LEFT JOIN user u ON u.id = a.actor_id"
    )

    def list_audit_entries(
        self, scope: dict[str, Any], filters: dict[str, Any], limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        where, params = self._audit_where(scope, filters)
        count_sql = " ".join(
            (
                "SELECT COUNT(*) AS total FROM audit_log a LEFT JOIN user u ON u.id = a.actor_id",
                "WHERE",
                where,
            )
        )
        count = self.conn.execute(count_sql, params).fetchone()
        rows_sql = " ".join((self.AUDIT_SELECT, "WHERE", where, "ORDER BY a.id DESC LIMIT ? OFFSET ?"))
        rows = self.conn.execute(rows_sql, (*params, int(limit), int(offset))).fetchall()
        return [dict(row) for row in rows], int(count["total"] if count is not None else 0)

    def _audit_where(self, scope: dict[str, Any], filters: dict[str, Any]) -> tuple[str, list[Any]]:
        where = ["1 = 1"]
        params: list[Any] = []
        owner_id = scope.get("owner_id")
        group_name = scope.get("group_name")
        if owner_id is not None:
            where.append("a.actor_id = ?")
            params.append(int(owner_id))
        elif group_name:
            where.append("u.group_name = ?")
            params.append(str(group_name))
        for column, key in (
            ("a.action", "action"),
            ("u.display_name", "actor"),
            ("a.target_type", "target_type"),
            ("a.target_id", "target_id"),
        ):
            value = filters.get(key)
            if value not in (None, ""):
                where.append(f"{column} = ?")
                params.append(str(value))
        if filters.get("created_from"):
            where.append("a.created_at >= ?")
            params.append(str(filters["created_from"]))
        if filters.get("created_before"):
            where.append("a.created_at < ?")
            params.append(str(filters["created_before"]))
        return " AND ".join(where), params
