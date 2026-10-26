# -*- coding: utf-8 -*-
"""兼容门面：域实现见 lesson_plan，旧调用保持 from lib import ... 不变。"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lesson_plan.examples import check_examples, example_entries, load_examples
from lesson_plan.jsonio import dump, load_json
from lesson_plan.model import (
    ACTIVITY_FLOW_LABELS,
    BLOCKING_SEVERITIES,
    C_LANGUAGE_TEMPLATES_PATH,
    EXAMPLES_DIR,
    EXAMPLES_INDEX,
    KNOWLEDGE_A,
    KNOWLEDGE_B,
    MIN_OVERRIDE_REASON,
    REQUIRED_FLOW,
    REQUIRED_TOP,
    REVIEW_SCHEMA_VERSION,
    RUBRIC_VERSION,
    RULES_VERSION,
    SCHOOL_DEFAULTS,
    SKILL_DIR,
    TEMPLATES_DIR,
    TOOL_VERSION,
    _activity_minutes,
    _finalize_findings,
    _nonempty,
    _normalise_text,
    _structured_activities,
    _structured_task_text,
    empty_flow,
    empty_plan,
    plan_hash,
)
from lesson_plan.validation import validate_plan


def draft_plan(
    week: int,
    session: int,
    content_title: str,
    *,
    content_detail: str = "",
    planned_hours: float = 2,
    academic_year: str = "2024-2025",
    semester: int = 2,
    teacher: str = "",
    teaching_object: str = "",
    teach_date: str = "",
    plan_number: str = "",
    student_context: str = "",
    must_do: str | None = None,
    optional: str | None = None,
) -> dict[str, Any]:
    knowledge = KNOWLEDGE_A if session % 2 == 1 else KNOWLEDGE_B
    must = must_do or ("第21套" if session % 2 == 1 else "第22套")
    opt = optional or ("第1套" if session % 2 == 1 else "第2套")
    if student_context.strip():
        intro = student_context.strip()
    elif week == 1:
        intro = "1、讲解这学期本课程的基本安排。2、讲解一级考证的重要性，重视课堂训练。3、强调课堂纪律。"
    else:
        intro = "1、讲解上次课遇到的难题。"
    goals = (
        "对上学期所学知识进行查漏补缺，争取通过一级考证。"
        if week == 1
        else "认真完成指定练习，争取通过一级考证。"
    )
    plan = empty_plan()
    plan.update(
        {
            "academicYear": academic_year,
            "semester": semester,
            "teacher": teacher,
            "teachingObject": teaching_object,
            "teachDate": teach_date,
            "planNumber": plan_number,
            "week": week,
            "session": session,
            "contentTitle": content_title,
            "contentDetail": content_detail,
            "plannedHours": planned_hours,
            "teachingPurpose": SCHOOL_DEFAULTS["teachingPurpose"],
            "knowledgeGoals": SCHOOL_DEFAULTS["knowledgeGoals"],
            "abilityGoals": SCHOOL_DEFAULTS["abilityGoals"],
            "qualityGoals": SCHOOL_DEFAULTS["qualityGoals"],
            "keyPoints": SCHOOL_DEFAULTS["keyPoints"],
        }
    )
    plan["activityFlow"] = {
        "introduction": intro,
        "learningGoals": goals,
        "knowledgeLearning": knowledge,
        "taskImplementation": (
            f"1、必须完成：完成{must}并提交结果文件\n"
            "2、完成标准：文件保存到指定位置，可现场演示关键操作\n"
            f"3、选做：{opt}"
        ),
        "assessment": "1、过程考核：依据现场操作记录评分（30）\n2、结果考核：依据提交的结果文件评分（70）",
        "summary": "评讲课堂学生遇到的难题",
        "homework": "课后复习选择题",
        "reflection": "课后根据课堂完成情况补充教学反思。",
    }
    topic = _match_c_language_template(content_title)
    if topic:
        plan.update({k: topic[k] for k in ("contentDetail", "teachingPurpose", "knowledgeGoals", "abilityGoals", "qualityGoals", "keyPoints") if k in topic})
        plan["activityFlow"] = topic["flow"]
    return plan


def _load_c_language_templates() -> list[dict[str, Any]]:
    try:
        raw = json.loads(C_LANGUAGE_TEMPLATES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return raw if isinstance(raw, list) else []


def _match_c_language_template(title: str) -> dict[str, Any] | None:
    """Select the most specific C-language topic by number of matched phrases."""
    title = str(title or "")
    best: dict[str, Any] | None = None
    best_score = 0
    for template in _load_c_language_templates():
        terms = template.get("match") or []
        score = sum(1 for term in terms if str(term) and str(term) in title)
        if score > best_score:
            best, best_score = template, score
    return best


def tokenize(text: str) -> set[str]:
    buf: list[str] = []
    cur: list[str] = []
    for ch in text.replace("\n", " "):
        if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff"):
            cur.append(ch)
        else:
            if len(cur) >= 2:
                buf.append("".join(cur))
            cur = []
    if len(cur) >= 2:
        buf.append("".join(cur))
    return set(buf)


def overlap_ratio(a: str, b: str) -> float:
    sa, sb = tokenize(a), tokenize(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa), len(sb))


GOAL_MARKERS = (
    "知道", "理解", "掌握", "学会", "能", "会", "说出", "识别", "区分",
    "完成", "写出", "操作", "演示", "提交", "运行", "解释", "设计",
    "列出", "描述", "运用", "分析", "比较",
)
OUTPUT_MARKERS = ("产出", "提交", "文件", "截图", "记录", "作品", "证据", "操作")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _nearest_sample(plan: dict[str, Any]) -> dict[str, Any] | None:
    samples = load_examples()
    if not samples:
        return None
    flow = plan.get("activityFlow") or {}
    best_path, best_ident, best_ov = samples[0][0], "", -1.0
    for path, sample in samples:
        ident = f"{sample.get('contentTitle')}-W{sample.get('week')}S{sample.get('session')}"
        ov = overlap_ratio(_text(plan.get("contentTitle")), _text(sample.get("contentTitle"))) * 0.3
        ov += overlap_ratio(
            _text(flow.get("knowledgeLearning")),
            _text((sample.get("activityFlow") or {}).get("knowledgeLearning")),
        ) * 0.7
        if ov > best_ov:
            best_path, best_ident, best_ov = path, ident, ov
    return {"id": best_ident, "overlap": round(best_ov, 4), "file": best_path.name}


def _score_dimension(dimension_id: str, name: str, checks: list[tuple]) -> dict[str, Any]:
    details = []
    failed_reasons = []
    suggestions = []
    earned = 0
    for check_id, points, passed, reason, suggestion in checks:
        details.append({"id": check_id, "points": points, "passed": passed, "reason": reason})
        if passed:
            earned += points
        else:
            if reason:
                failed_reasons.append(reason)
            if suggestion:
                suggestions.append(suggestion)
    return {
        "id": dimension_id,
        "name": name,
        "weight": sum(points for _, points, _, _, _ in checks),
        "score": earned,
        "checks": details,
        "reasons": failed_reasons,
        "suggestions": suggestions,
    }


def score_against_examples(plan: dict[str, Any]) -> dict[str, Any]:
    flow = plan.get("activityFlow") if isinstance(plan.get("activityFlow"), dict) else {}
    goals = {
        "知识目标": _text(plan.get("knowledgeGoals")),
        "能力目标": _text(plan.get("abilityGoals")),
        "素质目标": _text(plan.get("qualityGoals")),
    }
    missing_goals = [label for label, text in goals.items() if not text]
    weak_goals = [
        label for label in ("知识目标", "能力目标")
        if goals[label] and not any(marker in goals[label] for marker in GOAL_MARKERS)
    ]
    task = _text(flow.get("taskImplementation"))
    assessment = _text(flow.get("assessment"))
    summary = _text(flow.get("summary"))
    evidence_text = " ".join([task, assessment, summary])
    missing_steps = [key for key in REQUIRED_FLOW if not _text(flow.get(key))]

    goal_checks = [
        (
            "goal_fields", 10, not missing_goals,
            "缺少目标：" + "、".join(missing_goals),
            "补齐知识、能力、素质三维目标。",
        ),
        (
            "goal_observable", 15, not weak_goals and not missing_goals,
            "目标缺少可观察/可测量表述：" + "、".join(weak_goals),
            "用「说出/识别/完成/提交/操作」等可观察动词重写目标。",
        ),
    ]
    task_checks = [
        (
            "task_present", 10, bool(task),
            "缺少任务实施内容。",
            "在 activityFlow.taskImplementation 写明任务。",
        ),
        (
            "task_must_do", 10, any(marker in task for marker in ("必须完成", "必做")),
            "任务未区分必做与选做。",
            "用「必须完成：」标出全体学生必做任务。",
        ),
        (
            "task_output", 5, any(marker in task for marker in OUTPUT_MARKERS),
            "任务未说明可检查的产出。",
            "写明提交文件、截图或操作结果等产出。",
        ),
    ]
    assessment_checks = [
        (
            "assessment_present", 5, bool(assessment),
            "缺少考核方式。",
            "补充过程考核与结果考核。",
        ),
        (
            "assessment_process_result", 10,
            "过程" in assessment and any(marker in assessment for marker in ("结果", "考核", "评分", "占比", "%", "％")),
            "考核未同时覆盖过程与结果。",
            "分别写明过程考核与结果考核的占比或评分依据。",
        ),
        (
            "assessment_evidence", 5, any(marker in assessment for marker in OUTPUT_MARKERS),
            "考核未说明证据来源。",
            "把提交文件、操作记录等证据写入考核说明。",
        ),
    ]
    flow_checks = [
        (
            "flow_steps", 20, not missing_steps,
            "八步流程缺失：" + "、".join(missing_steps),
            "补齐八步流程的每一步。",
        ),
    ]
    evidence_checks = [
        (
            "evidence_output", 10, any(marker in evidence_text for marker in OUTPUT_MARKERS),
            "任务、考核与小结都没有可核验的产出证据。",
            "至少在一处写明产出、提交物或操作记录。",
        ),
    ]
    dimensions = [
        _score_dimension("goal", "目标可测", goal_checks),
        _score_dimension("task", "任务对应", task_checks),
        _score_dimension("assessment", "考核闭环", assessment_checks),
        _score_dimension("flow", "流程完整", flow_checks),
        _score_dimension("evidence", "证据可查", evidence_checks),
    ]
    total = sum(item["score"] for item in dimensions)
    if total >= 85:
        level = "优秀"
    elif total >= 70:
        level = "合格"
    else:
        level = "待改进"
    return {
        "score": total,
        "maxScore": 100,
        "ratio": round(total / 100, 4),
        "level": level,
        "dimensions": dimensions,
        "nearestSample": _nearest_sample(plan),
    }


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


def _refresh_report_status(report: dict[str, Any]) -> None:
    findings = [
        item for item in report.get("findings", [])
        if isinstance(item, dict)
    ]
    open_findings = [item for item in findings if item.get("status") == "open"]
    if open_findings:
        report["status"] = "needs_repair"
    elif any(
        item.get("severity") in BLOCKING_SEVERITIES and item.get("status") == "waived"
        for item in findings
    ):
        report["status"] = "passed_with_override"
    elif any(
        item.get("severity") == "minor" and item.get("status") == "accepted"
        for item in findings
    ):
        report["status"] = "passed_with_accepted_minor"


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


def default_review_path(plan_path: Path) -> Path:
    return plan_path.with_suffix(".review.json")


def load_review_report(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("审查报告必须是 JSON 对象")
    return data


def save_review_report(path: Path, report: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(dump(report) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path

