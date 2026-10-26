# -*- coding: utf-8 -*-
"""健康检查编排：汇总数据库、磁盘与插件引擎状态。"""
from __future__ import annotations

import sqlite3
from typing import Any

from app.adapters import engine, storage
from app.adapters.db.repo import Repo


def collect(connection: sqlite3.Connection | None) -> dict[str, Any]:
    database = Repo(connection).health() if connection is not None else "down"
    versions = engine.engine_versions()
    checks = {
        "database": database,
        "disk": storage.disk_status(),
        "engine": "down" if "status" in versions else "ok",
    }
    return {"ok": all(value == "ok" for value in checks.values()), "checks": checks, "versions": versions}
