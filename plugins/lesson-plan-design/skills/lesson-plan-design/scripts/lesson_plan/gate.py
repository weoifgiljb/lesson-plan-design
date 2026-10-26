# -*- coding: utf-8 -*-
"""审查状态、教师放行与导出门禁。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .model import (
    BLOCKING_SEVERITIES,
    MIN_OVERRIDE_REASON,
    REVIEW_SCHEMA_VERSION,
    RUBRIC_VERSION,
    TOOL_VERSION,
    plan_hash,
)
from .validation import validate_plan


def derive_review_status(findings: list[dict[str, Any]]) -> str:
    findings = [item for item in findings if isinstance(item, dict)]
    if any(item.get("status") == "open" for item in findings):
        return "needs_repair"
    if any(
        item.get("severity") in BLOCKING_SEVERITIES and item.get("status") == "waived"
        for item in findings
    ):
        return "passed_with_override"
    if any(
        item.get("severity") == "minor" and item.get("status") == "accepted"
        for item in findings
    ):
        return "passed_with_accepted_minor"
    return "passed"


def _refresh_report_status(report: dict[str, Any]) -> None:
    report["status"] = derive_review_status(report.get("findings", []))


def record_teacher_override(
    report: dict[str, Any],
    finding_id: str,
    *,
    teacher: str,
    reason: str,
    plan: dict[str, Any],
    strict_teacher: bool = False,
) -> dict[str, Any]:
    if not isinstance(plan, dict) or not plan:
        raise ValueError("教师放行需要当前教案")
    if not isinstance(report, dict):
        raise ValueError("审查报告格式无效")
    if report.get("planHash") != plan_hash(plan):
        raise ValueError("审查报告与当前教案内容不匹配")
    required_report = (
        "schemaVersion", "rubricVersion", "planHash", "round", "reviewer",
        "reviewedAt", "structuralValidation", "findings", "overrides", "repairHistory", "status",
    )
    if any(key not in report for key in required_report):
        raise ValueError("审查报告缺少必要字段")
    teacher_name = teacher.strip()
    reason_text = reason.strip()
    if not teacher_name or not reason_text:
        raise ValueError("教师姓名和放行原因不能为空")
    if len(reason_text) < MIN_OVERRIDE_REASON:
        raise ValueError(f"放行理由至少 {MIN_OVERRIDE_REASON} 个字")
    plan_teacher = str(plan.get("teacher") or "").strip()
    warning = ""
    if plan_teacher and teacher_name != plan_teacher:
        if strict_teacher:
            raise ValueError("放行者与教案任课教师不一致")
        warning = f"放行者 {teacher_name} 与任课教师 {plan_teacher} 不一致"
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("审查问题格式无效")
    overrides = report.get("overrides", [])
    if not isinstance(overrides, list):
        raise ValueError("审查放行记录格式无效")
    report["overrides"] = overrides
    finding = next((item for item in findings if isinstance(item, dict) and item.get("id") == finding_id), None)
    if not finding:
        raise ValueError(f"未找到审查问题：{finding_id}")
    severity = finding.get("severity")
    if severity not in {"blocker", "major", "minor"}:
        raise ValueError("审查问题严重级别无效")
    kind = "minor_acceptance" if severity == "minor" else "teacher_override"
    existing = next(
        (
            item for item in overrides
            if isinstance(item, dict)
            and item.get("findingId") == finding_id
            and item.get("planHash") == report.get("planHash")
        ),
        None,
    )
    if existing:
        if (
            existing.get("teacher") != teacher_name
            or existing.get("reason") != reason_text
            or (existing.get("kind") or "teacher_override") != kind
        ):
            raise ValueError("该问题已有放行或接受记录，不能重复提交")
        finding["status"] = "accepted" if severity == "minor" else "waived"
        _refresh_report_status(report)
        return existing
    override = {
        "findingId": finding_id,
        "kind": kind,
        "teacher": teacher_name,
        "reason": reason_text,
        "planHash": report.get("planHash"),
        "toolVersion": TOOL_VERSION,
        "approvedAt": datetime.now(timezone.utc).isoformat(),
    }
    if warning:
        override["warnings"] = [warning]
        report.setdefault("warnings", [])
        if warning not in report["warnings"]:
            report["warnings"].append(warning)
    overrides.append(override)
    finding["status"] = "accepted" if severity == "minor" else "waived"
    _refresh_report_status(report)
    return override


def export_gate(
    plan: dict[str, Any],
    report: dict[str, Any] | None,
    *,
    strict_independence: bool = False,
) -> dict[str, Any]:
    structural = validate_plan(plan)
    reasons: list[str] = []
    if not structural["ok"]:
        reasons.append("教案未通过结构校验")
    if report is None:
        reasons.append("缺少当前教案的对抗审查报告")
        return {"ok": False, "reasons": reasons, "structuralValidation": structural}
    if not isinstance(report, dict):
        reasons.append("审查报告格式无效")
        return {"ok": False, "reasons": reasons, "structuralValidation": structural}
    required_report = ("schemaVersion", "rubricVersion", "planHash", "round", "reviewer", "reviewedAt", "structuralValidation", "findings", "overrides", "repairHistory", "status", "attestation")
    if any(key not in report for key in required_report):
        reasons.append("审查报告缺少必要字段")
    if not isinstance(report.get("findings"), list) or len(report.get("findings") or []) > 1:
        reasons.append("审查报告必须包含至多一个最强反例")
    if not isinstance(report.get("overrides"), list) or not isinstance(report.get("repairHistory"), list):
        reasons.append("审查报告的审计记录格式无效")
    if report.get("schemaVersion") != REVIEW_SCHEMA_VERSION:
        reasons.append("审查报告版本不受支持")
    if report.get("rubricVersion") != RUBRIC_VERSION:
        reasons.append("审查量规版本不受支持")
    if report.get("planHash") != plan_hash(plan):
        reasons.append("审查报告与当前教案内容不匹配")
    snapshot = report.get("planSnapshot")
    if snapshot is not None:
        if not isinstance(snapshot, dict):
            reasons.append("审查报告快照格式无效")
        elif plan_hash(snapshot) != report.get("planHash"):
            reasons.append("审查报告快照与教案哈希不匹配")
    independence = report.get("independence") or report.get("reviewer")
    if independence not in {"native_subagent", "role_simulation", "human"}:
        reasons.append("审查报告审校方式无效")
    elif strict_independence and independence == "role_simulation":
        reasons.append("严格模式要求独立子代理审校")
    if not isinstance(report.get("structuralValidation"), dict) or not report["structuralValidation"].get("ok"):
        reasons.append("审查报告显示结构校验未通过")
    report_status = report.get("status")
    allowed_statuses = {
        "passed",
        "needs_repair",
        "structure_invalid",
        "pending_reviewer",
        "passed_with_override",
        "passed_with_accepted_minor",
    }
    if report_status not in allowed_statuses:
        reasons.append("审查报告状态无效")
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    valid_findings: list[dict[str, Any]] = []
    for item in findings:
        if not isinstance(item, dict):
            reasons.append("审查问题格式无效")
            continue
        valid_findings.append(item)
    findings = valid_findings
    current_hash = plan_hash(plan)
    finding_ids = {str(item.get("id")) for item in findings}
    overrides = report.get("overrides") if isinstance(report.get("overrides"), list) else []
    override_records: dict[str, str] = {}
    seen_override_ids: set[str] = set()
    for item in overrides:
        if not isinstance(item, dict):
            reasons.append("审查放行记录格式无效")
            continue
        if (
            not all(item.get(key) for key in ("findingId", "planHash", "teacher", "reason"))
            or not isinstance(item.get("teacher"), str)
            or not isinstance(item.get("reason"), str)
            or not item["teacher"].strip()
            or not item["reason"].strip()
        ):
            reasons.append("审查放行记录格式无效")
            continue
        if len(item["reason"].strip()) < MIN_OVERRIDE_REASON:
            reasons.append("审查放行理由过短")
        kind = item.get("kind") or "teacher_override"
        if kind not in {"teacher_override", "minor_acceptance"}:
            reasons.append("审查放行记录类型无效")
            continue
        if item.get("planHash") == current_hash:
            override_id = str(item["findingId"])
            if override_id in seen_override_ids:
                reasons.append("同一问题存在多条放行记录")
            seen_override_ids.add(override_id)
            override_records[override_id] = kind
    for override_id in override_records:
        if override_id not in finding_ids:
            reasons.append("放行记录引用了不存在的问题")
    for item in findings:
        severity = item.get("severity")
        status = item.get("status")
        if severity not in {"blocker", "major", "minor"}:
            reasons.append("审查问题严重级别无效")
        if status not in {"open", "waived", "accepted"}:
            reasons.append("审查问题状态无效")
            continue
        finding_id = str(item.get("id"))
        record_kind = override_records.get(finding_id)
        if status == "accepted" and severity != "minor":
            reasons.append("仅轻微问题可以标记为已接受")
        if status == "waived" and severity == "minor":
            reasons.append("轻微问题须由教师接受，不能按放行处理")
        if status == "open":
            reasons.append(f"存在未闭环的 {severity} 问题：{finding_id}")
        if status == "waived" and record_kind != "teacher_override":
            reasons.append(f"缺少与 waived 问题匹配的教师放行记录：{finding_id}")
        if status == "accepted" and record_kind != "minor_acceptance":
            reasons.append(f"缺少与 accepted 问题匹配的教师接受记录：{finding_id}")
    open_findings = [item for item in findings if item.get("status") == "open"]
    waived_blocking = [
        item for item in findings
        if item.get("severity") in BLOCKING_SEVERITIES and item.get("status") == "waived"
    ]
    accepted_minor = [
        item for item in findings
        if item.get("severity") == "minor" and item.get("status") == "accepted"
    ]
    if report_status == "pending_reviewer":
        reasons.append("审查尚未完成：缺少审校员反例或无反例声明")
    if report_status == "passed":
        if findings:
            reasons.append("通过的审查报告不能包含问题")
        if report.get("attestation") != "no_counterexample":
            reasons.append("通过的审查报告必须包含无反例声明")
    if report_status == "needs_repair" and not open_findings:
        reasons.append("待修复的审查报告必须包含未闭环问题")
    if report_status == "passed_with_override" and not waived_blocking:
        reasons.append("教师放行的审查报告必须包含已放行的 blocker 或 major 问题")
    if report_status == "passed_with_accepted_minor":
        if not accepted_minor:
            reasons.append("接受轻微问题的审查报告必须包含已接受的轻微问题")
        if waived_blocking:
            reasons.append("存在已放行的 blocker/major 时状态应为 passed_with_override")
    if report_status == "structure_invalid" and structural["ok"]:
        reasons.append("审查报告状态与结构校验结论不一致")
    return {"ok": not reasons, "reasons": reasons, "structuralValidation": structural}

