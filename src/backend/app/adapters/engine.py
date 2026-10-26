# -*- coding: utf-8 -*-
"""插件端引擎接入：全后端唯一修改 sys.path 的地方，保证两端哈希与校验一致。"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
PLUGIN_SCRIPTS = REPO_ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "scripts"


@lru_cache(maxsize=1)
def _lib() -> Any:
    target = str(PLUGIN_SCRIPTS)
    if target not in sys.path:
        sys.path.insert(0, target)
    import lib  # noqa: PLC0415 - 延迟导入，避免未装插件时影响后端启动

    return lib


def plan_hash(plan: dict[str, Any]) -> str:
    return _lib().plan_hash(plan)


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return _lib().validate_plan(plan)


def export_gate(plan: dict[str, Any], report: dict[str, Any] | None) -> dict[str, Any]:
    return _lib().export_gate(plan, report)


def engine_versions() -> dict[str, Any]:
    try:
        lib = _lib()
        return {
            "rulesVersion": lib.RULES_VERSION,
            "rubricVersion": lib.RUBRIC_VERSION,
            "reviewSchemaVersion": lib.REVIEW_SCHEMA_VERSION,
            "exampleCount": lib.check_examples().get("count", 0),
        }
    except Exception:  # noqa: BLE001 - 健康检查需要给出状态而不是 500
        return {"status": "unavailable"}
