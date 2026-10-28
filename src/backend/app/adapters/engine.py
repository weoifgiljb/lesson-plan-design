# -*- coding: utf-8 -*-
"""插件端引擎接入：全后端唯一修改 sys.path 的地方，保证两端哈希与校验一致。"""
from __future__ import annotations

import logging
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger("lpp")

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


def score_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """结构贴近分（0–100）：复用插件的五维评分，失败时降级为 0 分而不是 500。"""
    try:
        return _lib().score_against_examples(plan)
    except Exception as exc:  # noqa: BLE001 - 适配层统一兜底
        logger.warning("score_plan failed: %s", exc)
        return {"score": 0, "maxScore": 100, "level": "", "dimensions": []}


def export_docx(plan: dict[str, Any], output: Path, base_dir: Path | None = None) -> dict[str, Any]:
    """调用插件 export_docx 生成 DOCX；先写临时文件，成功后再原子替换。"""
    temporary = output.with_name(output.name + ".tmp")
    try:
        target = str(FORMATTING_SCRIPTS)
        if target not in sys.path:
            sys.path.insert(0, target)
        _lib()
        from export_docx import export_docx_result  # noqa: PLC0415

        output.parent.mkdir(parents=True, exist_ok=True)
        result = export_docx_result(plan, temporary, base_dir=base_dir)
        os.replace(temporary, output)
    except Exception as exc:  # noqa: BLE001 - 适配层统一转成可展示错误
        temporary.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        return {"ok": False, "code": "INTERNAL", "message": f"导出失败：{exc}"[:300]}
    finally:
        temporary.unlink(missing_ok=True)
    return {"ok": True, "result": result}


def engine_version() -> str:
    """从插件 footer 读取引擎版本；读取失败时返回空串，由调用方降级。"""
    try:
        text = FOOTER_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""
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
