# -*- coding: utf-8 -*-
"""设置：引擎与模板版本（只读）。"""
from __future__ import annotations

from typing import Any

from app.adapters import engine
from app.domain import versions


def engine_info() -> dict[str, Any]:
    info = engine.engine_versions()
    available = "status" not in info
    return {
        "engineAvailable": available,
        "versions": info,
        "contractVersion": "1",
        "supportedContractVersions": sorted(versions.SUPPORTED_CONTRACT_VERSIONS),
    }
