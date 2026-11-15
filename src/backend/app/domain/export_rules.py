# -*- coding: utf-8 -*-
"""导出前门禁：结构 + 当前报告 + 未关闭问题。"""
from __future__ import annotations

from typing import Any

from app.domain import versions
from app.domain.verdict import PASS, Verdict, fail

ALLOWED_REPORT_STATUS = {"passed", "passed_with_override", "passed_with_accepted_minor"}

#: 与插件端 lesson_plan/gate.py::export_gate 的 required_report 保持一致
REQUIRED_REPORT_KEYS = (
    "schemaVersion",
    "rubricVersion",
    "planHash",
    "round",
    "reviewer",
    "reviewedAt",
    "structuralValidation",
    "findings",
    "overrides",
    "repairHistory",
    "status",
    "attestation",
)


def report_shape_ok(report: dict[str, Any]) -> bool:
    """轻量结构守卫：必填键、审计记录类型与受支持的 schema/rubric 版本。

    只用于列表页按钮态，不替代引擎门禁：哈希匹配、结构校验、
    独立性与放行完整性仍由 export_service 复核。
    """
    if not isinstance(report, dict):
        return False
    if any(key not in report for key in REQUIRED_REPORT_KEYS):
        return False
    if not all(isinstance(report.get(key), list) for key in ("findings", "overrides", "repairHistory")):
        return False
    return versions.is_supported(report.get("schemaVersion"), report.get("rubricVersion"))



def gate(validation: dict[str, Any], report: dict[str, Any]) -> Verdict:
    if validation.get("ok") is not True:
        return fail(
            "STRUCTURE_INVALID",
            "教案未通过结构校验",
            {"issues": validation.get("issues", [])},
        )
    status = report.get("status")
    if status not in ALLOWED_REPORT_STATUS:
        return fail("REPORT_INCONSISTENT", f"报告状态不允许导出：{status}")
    findings = [item for item in (report.get("findings") or []) if isinstance(item, dict)]
    if any(item.get("status") == "open" for item in findings):
        return fail("REPORT_INCONSISTENT", "仍有关闭的问题，不能导出")
    return PASS
