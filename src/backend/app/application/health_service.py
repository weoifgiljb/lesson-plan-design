# -*- coding: utf-8 -*-
"""健康检查编排：汇总数据库、磁盘与插件引擎状态。"""
from __future__ import annotations

from typing import Any

from app.adapters import engine, storage
from app.adapters.db.repo import Repo


def collect(repo: Repo) -> dict[str, Any]:
    versions = engine.engine_versions()
    checks = {
        "database": repo.health(),
        "disk": storage.disk_status(),
        "engine": "down" if "status" in versions else "ok",
    }
    return {"ok": all(value == "ok" for value in checks.values()), "checks": checks, "versions": versions}
