# -*- coding: utf-8 -*-
"""MCP 工具实现与注册表；业务错误统一抛 ToolError。"""
from __future__ import annotations

from pathlib import Path

from export_docx import export_docx_result, self_check
from lib import (
    adversarial_review,
    draft_plan,
    dump,
    empty_plan,
    export_gate,
    record_teacher_override,
    score_against_examples,
    validate_plan,
)

from .errors import ToolError


def _result(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def tool_get_lesson_template(args: dict) -> dict:
    return _result(dump({"skeleton": empty_plan()}))


def tool_draft_lesson_plan(args: dict) -> dict:
    plan = draft_plan(
        int(args["week"]),
        int(args["session"]),
        str(args["contentTitle"]),
        content_detail=str(args.get("contentDetail") or ""),
        planned_hours=float(args.get("plannedHours") or 2),
        teacher=str(args.get("teacher") or ""),
        teaching_object=str(args.get("teachingObject") or ""),
    )
    return _result(dump({"plan": plan, "validation": validate_plan(plan)}))


def tool_validate_lesson_plan(args: dict) -> dict:
    return _result(
        dump(
            validate_plan(
                args.get("plan") or args,
                strict=bool(args.get("strict")),
                minutes_tolerance=_as_float(args.get("minutesTolerance")),
            )
        )
    )


def tool_start_adversarial_review(args: dict) -> dict:
    try:
        report = adversarial_review(
            args.get("plan") or args,
            round_number=int(args.get("round") or 1),
            finding=args.get("finding"),
            reviewer=str(args.get("reviewerMode") or "role_simulation"),
            previous_report=args.get("previousReport"),
            no_counterexample=bool(args.get("noCounterexample")),
        )
    except (TypeError, ValueError) as exc:
        raise ToolError("REVIEW_REJECTED", str(exc), "检查轮次、finding 或审校方式") from exc
    return _result(dump(report))


def tool_read_lesson_review(args: dict) -> dict:
    plan = args.get("plan") or {}
    report = args.get("reviewReport")
    gate = export_gate(plan, report)
    return _result(dump({"report": report, "valid": gate["ok"], "gate": gate}))


def tool_record_teacher_override(args: dict) -> dict:
    report = args.get("reviewReport") or {}
    try:
        override = record_teacher_override(
            report,
            str(args.get("issueId") or ""),
            teacher=str(args.get("teacher") or ""),
            reason=str(args.get("reason") or ""),
            plan=args.get("plan") or {},
            strict_teacher=bool(args.get("strictTeacher")),
        )
    except (TypeError, ValueError, AttributeError) as exc:
        raise ToolError("OVERRIDE_REJECTED", str(exc), "检查问题 ID、教师姓名与放行原因") from exc
    return _result(dump({"ok": True, "override": override, "reviewReport": report}))


def tool_export_lesson_docx(args: dict) -> dict:
    plan = args.get("plan") or args
    report = args.get("reviewReport")
    gate = export_gate(
        plan,
        report,
        strict_independence=bool(args.get("strictIndependence")),
    )
    if not gate["ok"]:
        raise ToolError(
            "GATE_REJECTED",
            "导出被门禁拒绝",
            "；".join(gate["reasons"]),
            {"reasons": gate["reasons"]},
        )
    out = Path(args.get("outputPath") or f"教案_第{plan.get('week')}周第{plan.get('session')}次.docx")
    base_dir = Path(str(args["baseDir"])) if args.get("baseDir") else out.parent
    independence = None
    if isinstance(report, dict):
        independence = report.get("independence") or report.get("reviewer")
    try:
        result = export_docx_result(
            plan,
            out,
            base_dir=base_dir,
            independence=independence,
            strict_metadata=bool(args.get("strictMetadata")),
        )
    except ValueError as exc:
        raise ToolError("INVALID_INPUT", str(exc), "检查导出参数", {"reasons": [str(exc)]}) from exc
    check = self_check(Path(result["path"]), plan, result["media"])
    if not check["ok"]:
        raise ToolError(
            "EXPORT_SELF_CHECK_FAILED",
            "导出后自检未通过",
            "检查页脚与媒体文件",
            {"selfCheck": check},
        )
    return _result(dump({
        "ok": True,
        "path": str(result["path"]),
        "bytes": Path(result["path"]).stat().st_size,
        "engineVersion": result["engineVersion"],
        "selfCheck": check,
        "warnings": result["warnings"],
    }))


def tool_score_against_samples(args: dict) -> dict:
    return _result(dump(score_against_examples(args.get("plan") or args)))


TOOL_HANDLERS = {
    "get_lesson_template": tool_get_lesson_template,
    "draft_lesson_plan": tool_draft_lesson_plan,
    "validate_lesson_plan": tool_validate_lesson_plan,
    "start_adversarial_review": tool_start_adversarial_review,
    "read_lesson_review": tool_read_lesson_review,
    "record_teacher_override": tool_record_teacher_override,
    "export_lesson_docx": tool_export_lesson_docx,
    "score_against_samples": tool_score_against_samples,
}


def invoke_tool(name: str, args: dict) -> dict:
    if not isinstance(args, dict):
        raise ToolError("INVALID_PARAMS", "工具参数必须是 JSON 对象", "检查 arguments")
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise ToolError("METHOD_NOT_FOUND", f"未知工具：{name}", "检查 tools/list")
    return handler(args)
