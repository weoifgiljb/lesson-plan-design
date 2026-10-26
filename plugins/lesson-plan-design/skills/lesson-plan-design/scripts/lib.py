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

from lesson_plan.gate import (  # noqa: E402
    _refresh_report_status,
    derive_review_status,
    export_gate,
    record_teacher_override,
)
from lesson_plan.review import adversarial_review  # noqa: E402
from lesson_plan.review_store import (  # noqa: E402
    default_review_path,
    load_review_report,
    save_review_report,
)
