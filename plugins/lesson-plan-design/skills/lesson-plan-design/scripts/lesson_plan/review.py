# -*- coding: utf-8 -*-
"""对抗审查：finding、预检、报告轮次。"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .model import (
    REVIEW_SCHEMA_VERSION,
    RUBRIC_VERSION,
    TOOL_VERSION,
    _nonempty,
    _structured_activities,
    plan_hash,
)
from .validation import validate_plan


def _finding(
    plan: dict[str, Any],
    *,
    hypothesis: str,
    severity: str,
    evidence: list[str],
    affected_paths: list[str],
    why: str,
    repair: str,
    round_number: int,
) -> dict[str, Any]:
    key = f"{plan_hash(plan)}:{hypothesis}:{'|'.join(affected_paths)}".encode("utf-8")
    return {
        "id": f"AR-{hashlib.sha256(key).hexdigest()[:10]}",
        "round": round_number,
        "severity": severity,
        "hypothesis": hypothesis,
        "evidence": evidence,
        "affectedPaths": affected_paths,
        "whyItBreaksTheLoop": why,
        "minimalRepair": repair,
        "status": "open",
    }


def _normalise_finding(plan: dict[str, Any], finding: dict[str, Any], round_number: int) -> dict[str, Any]:
    if not isinstance(finding, dict):
        raise ValueError("审查发现必须是 JSON 对象")
    required = ("severity", "hypothesis", "evidence", "affectedPaths", "whyItBreaksTheLoop", "minimalRepair")
    missing = [key for key in required if not finding.get(key)]
    if missing:
        raise ValueError(f"审查发现缺少字段：{', '.join(missing)}")
    if not isinstance(finding["evidence"], list) or not all(isinstance(item, str) and item.strip() for item in finding["evidence"]):
        raise ValueError("审查发现 evidence 必须是非空字符串列表")
    if not isinstance(finding["affectedPaths"], list) or not all(isinstance(item, str) and item.strip() for item in finding["affectedPaths"]):
        raise ValueError("审查发现 affectedPaths 必须是非空字符串列表")
    severity = str(finding["severity"]).lower()
    if severity not in {"blocker", "major", "minor"}:
        raise ValueError("严重级别须为 blocker、major 或 minor")
    paths = list(finding["affectedPaths"])
    item = _finding(
        plan,
        hypothesis=str(finding["hypothesis"]),
        severity=severity,
        evidence=[str(item) for item in finding["evidence"]],
        affected_paths=[str(path) for path in paths],
        why=str(finding["whyItBreaksTheLoop"]),
        repair=str(finding["minimalRepair"]),
        round_number=round_number,
    )
    return item


def _preflight_adversarial_finding(plan: dict[str, Any], round_number: int) -> dict[str, Any] | None:
    """Catch one deterministic counterexample; agents supply deeper pedagogical judgment."""
    flow = plan.get("activityFlow") or {}
    # Structured activities must expose a learner action and a verifiable output
    # in the implementation step; otherwise the activity cannot close the loop.
    task_rows = _structured_activities(flow.get("taskImplementation"))
    if task_rows is not None:
        missing_student = [i for i, row in enumerate(task_rows) if not _nonempty(row.get("studentActivity"))]
        missing_output = [i for i, row in enumerate(task_rows) if not (_nonempty(row.get("evidence")) or _nonempty(row.get("output")))]
        if missing_student:
            return _finding(
                plan,
                hypothesis="structured_activity_without_student_action",
                severity="major",
                evidence=[f"activityFlow.taskImplementation[{i}] 缺少 studentActivity" for i in missing_student],
                affected_paths=[f"activityFlow.taskImplementation[{i}].studentActivity" for i in missing_student],
                why="结构化任务只有教师安排，没有明确的学生操作，能力目标无法在课堂内观察。",
                repair="补充学生具体操作步骤或协作方式。",
                round_number=round_number,
            )
        if missing_output:
            return _finding(
                plan,
                hypothesis="structured_activity_without_verifiable_output",
                severity="major",
                evidence=[f"activityFlow.taskImplementation[{i}] 缺少 evidence/output" for i in missing_output],
                affected_paths=[f"activityFlow.taskImplementation[{i}].evidence" for i in missing_output],
                why="任务没有可提交或可观察的产出，无法判断学生是否完成。",
                repair="增加文件、截图、运行结果或现场演示等核验产出。",
                round_number=round_number,
            )
    else:
        task = str(flow.get("taskImplementation") or "").strip()
        task_terms = ("提交", "作品", "文件", "完成标准", "操作记录")
        if task and not any(term in task for term in task_terms):
            return _finding(
                plan,
                hypothesis="task_not_executable",
                severity="major",
                evidence=[f"activityFlow.taskImplementation: {task}"],
                affected_paths=["activityFlow.taskImplementation"],
                why="任务没有可核验的产出或完成标准，学生完成与否无法判断。",
                repair="说明学生须提交的产出、完成标准或可观察的操作记录。",
                round_number=round_number,
            )
    assessment_rows = _structured_activities(flow.get("assessment"))
    assessment = "" if assessment_rows is not None else str(flow.get("assessment") or "").strip()
    observable_terms = ("作品", "提交", "操作", "演示", "记录", "文件", "答题", "完成情况", "评分标准")
    if assessment and not any(term in assessment for term in observable_terms):
        return _finding(
            plan,
            hypothesis="assessment_cannot_prove_learning",
            severity="major",
            evidence=[f"activityFlow.assessment: {assessment}"],
            affected_paths=["activityFlow.assessment"],
            why="考核只给出分值或笼统名称，未说明以何种学生产出或操作证据判断目标达成。",
            repair="明确提交物或现场操作，并说明其对应的目标与评分依据。",
            round_number=round_number,
        )
    return None


def adversarial_review(
    plan: dict[str, Any],
    *,
    round_number: int = 1,
    finding: dict[str, Any] | None = None,
    reviewer: str = "role_simulation",
    previous_report: dict[str, Any] | None = None,
    no_counterexample: bool = False,
) -> dict[str, Any]:
    """Build one immutable review round; no mutation of the lesson plan occurs here."""
    if previous_report is not None and not isinstance(previous_report, dict):
        raise ValueError("previousReport 必须是 JSON 对象")
    if reviewer not in {"native_subagent", "role_simulation", "human"}:
        raise ValueError("审校方式无效")
    if finding and no_counterexample:
        raise ValueError("不能同时提交反例并声明无反例")
    if previous_report is not None:
        previous_round = previous_report.get("round")
        if not isinstance(previous_round, int) or previous_round < 1:
            raise ValueError("上一轮报告缺少有效轮次")
        expected_round = previous_round + 1
    else:
        expected_round = 1
    if round_number != expected_round:
        raise ValueError(f"轮次必须为 {expected_round}，收到 {round_number}")
    plan_snapshot = json.loads(json.dumps(plan, ensure_ascii=False))
    duplicate_review = bool(
        previous_report is not None and previous_report.get("planHash") == plan_hash(plan)
    )
    structural = validate_plan(plan)
    report: dict[str, Any] = {
        "schemaVersion": REVIEW_SCHEMA_VERSION,
        "rubricVersion": RUBRIC_VERSION,
        "toolVersion": TOOL_VERSION,
        "planHash": plan_hash(plan),
        "planSnapshot": plan_snapshot,
        "round": round_number,
        "duplicateReview": duplicate_review,
        "reviewer": reviewer,
        "independence": reviewer,
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
        "structuralValidation": {key: value for key, value in structural.items() if key != "plan"},
        "findings": [],
        "overrides": [],
        "repairHistory": [],
        "attestation": None,
    }
    if previous_report is not None:
        report["repairHistory"] = list(previous_report.get("repairHistory", [])) + [
            {
                "round": previous_report.get("round"),
                "planHash": previous_report.get("planHash"),
                "status": previous_report.get("status"),
            }
        ]
    if not structural["ok"]:
        report["status"] = "structure_invalid"
        report["conclusion"] = "结构校验未通过，不能进入教学质量对抗审查。"
        return report

    preflight = _preflight_adversarial_finding(plan, round_number)
    reported = _normalise_finding(plan, finding, round_number) if finding else None
    severity_rank = {"minor": 1, "major": 2, "blocker": 3}
    strongest = max(
        (item for item in (preflight, reported) if item),
        key=lambda item: severity_rank[item["severity"]],
        default=None,
    )
    if strongest:
        report["findings"] = [strongest]
        report["status"] = "needs_repair"
        report["conclusion"] = "发现一个需独立修复 Agent 处理的最强反例。"
    elif no_counterexample:
        report["status"] = "passed"
        report["attestation"] = "no_counterexample"
        report["conclusion"] = "审校员确认本轮未能证明教学闭环失效。"
    else:
        report["status"] = "pending_reviewer"
        report["conclusion"] = "审查尚未完成：需要审校员提交反例或明确声明无反例。"
    return report
