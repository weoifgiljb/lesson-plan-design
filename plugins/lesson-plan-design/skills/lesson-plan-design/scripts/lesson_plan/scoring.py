# -*- coding: utf-8 -*-
"""五维评分与最近样例。"""
from __future__ import annotations

from typing import Any

from .examples import load_examples
from .model import REQUIRED_FLOW


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
