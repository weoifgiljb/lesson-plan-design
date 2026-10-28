# -*- coding: utf-8 -*-
"""插件端引擎接入：全后端唯一修改 sys.path 的地方，保证两端哈希与校验一致。"""
from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
PLUGIN_SCRIPTS = REPO_ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "scripts"
FORMATTING_SCRIPTS = REPO_ROOT / "plugins" / "lesson-plan-design" / "skills" / "formatting-lesson-docx" / "scripts"
FOOTER_PATH = PLUGIN_SCRIPTS / "docx_export" / "footer.py"
ENGINE_VERSION_RE = re.compile(r"^\s*ENGINE_VERSION\s*=\s*\"([^\"]+)\"", re.M)


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


def export_docx(plan: dict[str, Any], output: Path, base_dir: Path | None = None) -> dict[str, Any]:
    """调用插件 export_docx 生成 DOCX；失败以返回值表达，不向调用方抛异常。"""
    target = str(FORMATTING_SCRIPTS)
    if target not in sys.path:
        sys.path.insert(0, target)
    _lib()
    from export_docx import export_docx_result  # noqa: PLC0415

    try:
        result = export_docx_result(plan, output, base_dir=base_dir)
    except Exception as exc:  # noqa: BLE001 - 适配层统一转成可展示错误
        return {"ok": False, "code": "INTERNAL", "message": f"导出失败：{exc}"[:300]}
    return {"ok": True, "result": result}


def engine_version() -> str:
    """从插件 footer 读取引擎版本；只读源码，不 import python-docx 依赖。"""
    text = FOOTER_PATH.read_text(encoding="utf-8")
    match = ENGINE_VERSION_RE.search(text)
    return match.group(1) if match else ""


def engine_versions() -> dict[str, Any]:
    try:
        lib = _lib()
        return {
            "engineVersion": engine_version(),
            "rulesVersion": lib.RULES_VERSION,
            "rubricVersion": lib.RUBRIC_VERSION,
            "reviewSchemaVersion": lib.REVIEW_SCHEMA_VERSION,
            "exampleCount": lib.check_examples().get("count", 0),
        }
    except Exception:  # noqa: BLE001 - 健康检查需要给出状态而不是 500
        return {"status": "unavailable"}
