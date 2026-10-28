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
from app.domain.errors import AppError


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class Repo:
    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock | None = None) -> None:
        self.conn = conn
        self.lock = lock

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

    def user_by_display_name(self, display_name: str) -> dict[str, Any] | None:
        return _row(
            self.conn.execute("SELECT * FROM user WHERE display_name = ? AND active = 1", (display_name,)).fetchone()
        )

    def insert_user(self, username: str, display_name: str, role: str, password_hash: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO user (username, display_name, role, password_hash, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (username, display_name, role, password_hash, clock.now_iso()),
        )
        return int(cursor.lastrowid or 0)

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
                " review.id AS review_id, plan_version.plan_id AS plan_id"
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
        report_sha256: str, schema_version: int, rubric_version: str,
    ) -> tuple[int, bool]:
        try:
            cursor = self.conn.execute(
                "INSERT INTO plan_version (plan_id, version_no, content_json, plan_hash, report_sha256,"
                " schema_version, rubric_version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    plan_id, version_no, content_json, plan_hash, report_sha256,
                    schema_version, rubric_version, clock.now_iso(),
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
