# -*- coding: utf-8 -*-
"""证据链五项：哈希匹配、轮次连续、放行完整、审校方式合规、状态一致。"""
from __future__ import annotations

from typing import Any

from app.domain import report_rules

ALLOWED_MODES = {"native_subagent", "role_simulation", "human"}
BLOCKING = {"blocker", "major"}
MIN_REASON = 6
ALLOWED_STATUS = report_rules.ALLOWED_STATUS

LABELS = {
    "hash_match": "哈希匹配",
    "round_continuous": "轮次连续",
    "overrides_complete": "放行完整",
    "independence_valid": "审校方式合规",
    "status_consistent": "状态一致",
}


def evaluate(
    report: dict[str, Any],
    *,
    plan_hash: str,
    rounds: list[int],
    snapshot_hash: str | None,
) -> dict[str, Any]:
    items = [
        _item("hash_match", _hash_problem(report, plan_hash, snapshot_hash)),
        _item("round_continuous", _round_problem(report, rounds)),
        _item("overrides_complete", _override_problem(report)),
        _item("independence_valid", _independence_problem(report)),
        _item("status_consistent", _status_problem(report)),
    ]
    passed = sum(1 for item in items if item["ok"])
    return {
        "items": items,
        "complete": passed == len(items),
        "passed": passed,
        "total": len(items),
        "gaps": [item["key"] for item in items if not item["ok"]],
    }


def _is_member(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _item(key: str, problem: str | None) -> dict[str, Any]:
    return {"key": key, "label": LABELS[key], "ok": problem is None, "reason": problem or ""}


def _hash_problem(report: dict[str, Any], plan_hash: str, snapshot_hash: str | None) -> str | None:
    if report.get("planHash") != plan_hash:
        return "报告哈希与教案版本不一致"
    if snapshot_hash is not None and snapshot_hash != plan_hash:
        return "报告快照哈希与教案版本不一致"
    return None


def _round_problem(report: dict[str, Any], rounds: list[int]) -> str | None:
    round_number = report.get("round")
    if not isinstance(round_number, int) or isinstance(round_number, bool) or round_number < 1:
        return "报告轮次无效"
    if len(set(rounds)) != len(rounds):
        return "同一教案存在重复轮次"
    missing = [value for value in range(1, round_number + 1) if value not in rounds]
    if missing:
        return f"轮次不连续，缺少第 {missing[0]} 轮"
    return None


def _override_problem(report: dict[str, Any]) -> str | None:
    findings = report.get("findings") or []
    overrides = report.get("overrides") or []
    if not isinstance(findings, list) or not isinstance(overrides, list):
        return "问题或放行记录格式无效"
    problem = _finding_shape_problem(findings)
    if problem is not None:
        return problem
    kinds = {}
    for item in overrides:
        if not isinstance(item, dict):
            return "放行记录格式无效"
        finding_id = item.get("findingId")
        if not finding_id or item.get("planHash") != report.get("planHash"):
            return "放行记录缺少 findingId 或哈希不符"
        if not str(item.get("teacher") or "").strip():
            return f"放行记录缺少教师：{finding_id}"
        if len(str(item.get("reason") or "").strip()) < MIN_REASON:
            return f"放行理由过短：{finding_id}"
        if not _is_member(item.get("kind"), {"teacher_override", "minor_acceptance"}):
            return f"放行类型无效：{finding_id}"
        if finding_id in kinds:
            return f"同一问题存在多条放行记录：{finding_id}"
        kinds[finding_id] = item["kind"]
    finding_ids = {str(item.get("id")) for item in findings}
    for finding_id in kinds:
        if finding_id not in finding_ids:
            return f"放行记录引用了不存在的问题：{finding_id}"
    for item in findings:
        status = item.get("status")
        if not _is_member(status, {"waived", "accepted"}):
            continue
        expected = "minor_acceptance" if status == "accepted" else "teacher_override"
        if kinds.get(str(item.get("id"))) != expected:
            return f"{status} 问题缺少对应放行记录：{item.get('id')}"
    return None


def _finding_shape_problem(findings: list[Any]) -> str | None:
    for item in findings:
        if not isinstance(item, dict):
            return "问题格式无效（不是对象）"
        severity = item.get("severity")
        status = item.get("status")
        if not _is_member(severity, {"blocker", "major", "minor"}):
            return f"问题严重级别无效：{item.get('id')}"
        if not _is_member(status, {"open", "waived", "accepted"}):
            return f"问题状态无效：{item.get('id')}"
        if status == "accepted" and severity != "minor":
            return "仅轻微问题可以标记为已接受"
        if status == "waived" and severity == "minor":
            return "轻微问题须由教师接受，不能按放行处理"
    return None


def _independence_problem(report: dict[str, Any]) -> str | None:
    mode = report.get("independence") or report.get("reviewer")
    if not _is_member(mode, ALLOWED_MODES):
        return f"审校方式无效：{mode}"
    if not str(report.get("reviewer") or "").strip():
        return "缺少审校员"
    return None


def _status_problem(report: dict[str, Any]) -> str | None:
    status = report.get("status")
    if not _is_member(status, ALLOWED_STATUS):
        return f"报告状态无效：{status}"
    raw_findings = report.get("findings") or []
    if not isinstance(raw_findings, list) or any(not isinstance(item, dict) for item in raw_findings):
        return "问题格式无效"
    findings = raw_findings
    structural = report.get("structuralValidation")
    structural_ok = isinstance(structural, dict) and structural.get("ok") is True
    if not structural_ok:
        return None if status == "structure_invalid" else "结构未通过但状态不是 structure_invalid"
    if status == "structure_invalid":
        return "结构已通过但状态为 structure_invalid"
    if status == "pending_reviewer":
        return None if not findings else "待审报告不应包含问题"
    derived = report_rules.derive_status(findings)
    if status != derived:
        return f"状态与问题闭环不一致：报告 {status}，推导 {derived}"
    if status == "passed" and report.get("attestation") != "no_counterexample":
        return "通过的报告缺少无反例声明"
    if status == "passed_with_override" and not any(
        _is_member(item.get("severity"), BLOCKING) and item.get("status") == "waived" for item in findings
    ):
        return "放行通过的报告没有已放行的 blocker/major"
    if status == "passed_with_accepted_minor" and not any(
        item.get("severity") == "minor" and item.get("status") == "accepted" for item in findings
    ):
        return "接受轻微问题的报告没有已接受的 minor"
    return None
