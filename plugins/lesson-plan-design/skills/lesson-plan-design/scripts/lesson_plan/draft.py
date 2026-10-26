# -*- coding: utf-8 -*-
"""教案草稿与 C 语言模板匹配。"""
from __future__ import annotations

import json
from typing import Any

from .model import (
    C_LANGUAGE_TEMPLATES_PATH,
    KNOWLEDGE_A,
    KNOWLEDGE_B,
    SCHOOL_DEFAULTS,
    empty_plan,
)


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

