# -*- coding: utf-8 -*-
"""事务边界：busy 重试失败时不得误发 ROLLBACK（否则 409 会被 500 覆盖）。"""
from __future__ import annotations

import sqlite3
import unittest

from app.adapters.db.repo import Repo
from app.domain.errors import AppError


class FakeConnection:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, sql: str, *args, **kwargs):
        self.calls.append(sql.strip())
        if sql.strip().lower().startswith("begin"):
            raise sqlite3.OperationalError("database is locked")
        raise AssertionError(f"unexpected SQL: {sql}")

    def close(self) -> None:
        return None


class TestTransactionBoundary(unittest.TestCase):
    def test_busy_retry_raises_conflict_without_rollback(self) -> None:
        connection = FakeConnection()
        repo = Repo(connection)
        with self.assertRaises(AppError) as caught:
            with repo.transaction():
                self.fail("busy 时不应进入事务体")
        self.assertEqual(caught.exception.code, "CONFLICT_STALE")
        self.assertEqual(len(connection.calls), 3)
        self.assertFalse(any(call.lower().startswith("rollback") for call in connection.calls))


if __name__ == "__main__":
    unittest.main()
