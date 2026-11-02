# -*- coding: utf-8 -*-
"""导出前门禁：结构 + 当前报告 + 未关闭问题。"""
from __future__ import annotations

from typing import Any

from app.domain.verdict import PASS, Verdict, fail

ALLOWED_REPORT_STATUS = {"passed", "passed_with_override", "passed_with_accepted_minor"}


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
