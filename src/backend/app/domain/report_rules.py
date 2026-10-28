# -*- coding: utf-8 -*-
"""审查报告一致性规则：平台独立复算状态，不采信报告自述。"""
from __future__ import annotations

from typing import Any

from app.domain import versions
from app.domain.verdict import Verdict, fail

ALLOWED_STATUS = {
    "structure_invalid",
    "pending_reviewer",
    "needs_repair",
    "passed",
    "passed_with_override",
    "passed_with_accepted_minor",
}
ALLOWED_SEVERITY = {"blocker", "major", "minor"}
ALLOWED_FINDING_STATUS = {"open", "waived", "accepted"}
ALLOWED_INDEPENDENCE = {"native_subagent", "role_simulation", "human"}
BLOCKING = {"blocker", "major"}
MIN_OVERRIDE_REASON = 6
REQUIRED_REPORT = (
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


def derive_status(findings: list[dict[str, Any]]) -> str:
    items = [item for item in findings if isinstance(item, dict)]
    if any(item.get("status") == "open" for item in items):
        return "needs_repair"
    if any(item.get("severity") in BLOCKING and item.get("status") == "waived" for item in items):
        return "passed_with_override"
    if any(item.get("severity") == "minor" and item.get("status") == "accepted" for item in items):
        return "passed_with_accepted_minor"
    return "passed"


def _check_findings(report: dict[str, Any], plan_hash: str) -> Verdict | None:
    findings = report.get("findings")
    if not isinstance(findings, list) or len(findings) > 1:
        return fail("REPORT_INCONSISTENT", "审查报告必须包含至多一个最强反例")
    overrides = report.get("overrides")
    if not isinstance(overrides, list):
        return fail("REPORT_INCONSISTENT", "审查放行记录格式无效")
    finding_ids = {str(item.get("id")) for item in findings if isinstance(item, dict)}
    seen: set[str] = set()
    for item in findings:
        if not isinstance(item, dict):
            return fail("REPORT_INCONSISTENT", "审查问题格式无效")
        if not item.get("id") or item.get("severity") not in ALLOWED_SEVERITY:
            return fail("REPORT_INCONSISTENT", "审查问题缺少 id 或严重级别")
        if item.get("status") not in ALLOWED_FINDING_STATUS:
            return fail("REPORT_INCONSISTENT", "审查问题状态无效")
    for item in overrides:
        problem = _check_override(item, plan_hash, finding_ids, seen)
        if problem is not None:
            return problem
    return _check_finding_override_pairs(findings, overrides)


def _check_override(item: Any, plan_hash: str, finding_ids: set[str], seen: set[str]) -> Verdict | None:
    if not isinstance(item, dict):
        return fail("REPORT_INCONSISTENT", "审查放行记录格式无效")
    needed = ("findingId", "planHash", "teacher", "reason")
    if not all(item.get(key) for key in needed):
        return fail("REPORT_INCONSISTENT", "审查放行记录缺少必要字段")
    if not isinstance(item.get("teacher"), str) or not isinstance(item.get("reason"), str):
        return fail("REPORT_INCONSISTENT", "审查放行记录字段类型无效")
    if len(item["reason"].strip()) < MIN_OVERRIDE_REASON:
        return fail("REPORT_INCONSISTENT", "审查放行理由过短")
    if item.get("planHash") != plan_hash:
        return fail("REPORT_INCONSISTENT", "放行记录与当前教案哈希不一致")
    if item.get("kind") not in {"teacher_override", "minor_acceptance"}:
        return fail("REPORT_INCONSISTENT", "审查放行记录类型无效")
    finding_id = str(item["findingId"])
    if finding_id in seen:
        return fail("REPORT_INCONSISTENT", "同一问题存在多条放行记录")
    if finding_id not in finding_ids:
        return fail("REPORT_INCONSISTENT", "放行记录引用了不存在的问题")
    seen.add(finding_id)
    return None


def _check_finding_override_pairs(findings: list[dict[str, Any]], overrides: list[dict[str, Any]]) -> Verdict | None:
    kinds = {str(item["findingId"]): item["kind"] for item in overrides}
    for item in findings:
        finding_id = str(item.get("id"))
        severity = item.get("severity")
        status = item.get("status")
        if status == "open":
            return fail("REPORT_INCONSISTENT", f"存在未闭环的 {severity} 问题：{finding_id}")
        if status == "accepted" and severity != "minor":
            return fail("REPORT_INCONSISTENT", "仅轻微问题可以标记为已接受")
        if status == "waived" and severity == "minor":
            return fail("REPORT_INCONSISTENT", "轻微问题须由教师接受，不能按放行处理")
        expected = "minor_acceptance" if status == "accepted" else "teacher_override"
        if kinds.get(finding_id) != expected:
            return fail("REPORT_INCONSISTENT", f"缺少与 {status} 问题匹配的放行记录：{finding_id}")
    return None


def _check_status(report: dict[str, Any], structural_ok: bool) -> Verdict | None:
    status = report.get("status")
    if status not in ALLOWED_STATUS:
        return fail("REPORT_INCONSISTENT", "审查报告状态无效")
    findings = report.get("findings") or []
    if not structural_ok or status == "structure_invalid":
        if structural_ok or status != "structure_invalid":
            return fail("REPORT_INCONSISTENT", "审查报告状态与结构校验结论不一致")
        return None
    if status == "pending_reviewer":
        if findings:
            return fail("REPORT_INCONSISTENT", "待审报告不能包含问题")
        return None
    if status != derive_status(findings):
        return fail("REPORT_INCONSISTENT", "审查报告状态与问题闭环情况不一致")
    if status == "passed" and report.get("attestation") != "no_counterexample":
        return fail("REPORT_INCONSISTENT", "通过的审查报告必须包含无反例声明")
    return None


def check(
    report: dict[str, Any],
    *,
    plan_hash: str,
    snapshot_hash: str | None,
    structural_ok: bool,
    previous_round: int,
) -> Verdict | None:
    if not isinstance(report, dict):
        return fail("REPORT_INCONSISTENT", "审查报告格式无效")
    missing = [key for key in REQUIRED_REPORT if key not in report]
    if missing:
        return fail("REPORT_INCONSISTENT", "审查报告缺少必要字段", {"missing": missing})
    if not versions.is_supported(report.get("schemaVersion"), report.get("rubricVersion")):
        return fail("SCHEMA_UNSUPPORTED", "审查报告版本不受支持", versions.supported_versions())
    if not isinstance(report.get("round"), int) or isinstance(report.get("round"), bool):
        return fail("REPORT_INCONSISTENT", "审查轮次必须是正整数")
    if report["round"] != previous_round + 1:
        return fail(
            "REPORT_INCONSISTENT",
            f"审查轮次必须为 {previous_round + 1}，收到 {report['round']}",
        )
    if report.get("planHash") != plan_hash:
        return fail("REPORT_INCONSISTENT", "审查报告与当前教案内容不匹配")
    independence = report.get("independence") or report.get("reviewer")
    if independence not in ALLOWED_INDEPENDENCE:
        return fail("REPORT_INCONSISTENT", "审查报告审校方式无效", {"independence": independence})
    if snapshot_hash is not None and snapshot_hash != plan_hash:
        return fail("REPORT_INCONSISTENT", "审查报告快照与教案哈希不匹配")
    structural = report.get("structuralValidation")
    if not isinstance(structural, dict) or structural.get("ok") is not True:
        return fail("REPORT_INCONSISTENT", "审查报告显示结构校验未通过")
    findings_problem = _check_findings(report, plan_hash)
    if findings_problem is not None:
        return findings_problem
    return _check_status(report, structural_ok)
