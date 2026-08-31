# -*- coding: utf-8 -*-
"""校标教案共享逻辑：schema、草稿、校验、评分。仅标准库。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = SKILL_DIR / "examples"
TEMPLATES_DIR = SKILL_DIR / "templates"

ACTIVITY_FLOW_LABELS = {
    "introduction": "一、复习与导入新课",
    "learningGoals": "二、明确学习目标",
    "knowledgeLearning": "三、知识学习",
    "taskImplementation": "四、工作任务实施",
    "assessment": "五、课程考核",
    "summary": "六、课堂小结",
    "homework": "七、布置作业",
    "reflection": "八、教学反思",
}

REQUIRED_TOP = [
    "school",
    "academicYear",
    "semester",
    "course",
    "teachingGroup",
    "week",
    "session",
    "contentTitle",
    "plannedHours",
    "teachingPurpose",
    "knowledgeGoals",
    "abilityGoals",
    "qualityGoals",
    "keyPoints",
    "teachingMethods",
    "teachingResources",
    "activityFlow",
]

REQUIRED_FLOW = [
    "introduction",
    "learningGoals",
    "knowledgeLearning",
    "taskImplementation",
    "assessment",
    "summary",
    "homework",
]

SCHOOL_DEFAULTS = {
    "school": "东莞经贸学校",
    "course": "信息技术",
    "teachingGroup": "计算机",
    "teachingMethods": "教法：讲授法、演示法、学法：实操法 自主探究法",
    "teachingResources": "机房、课堂练习一份",
    "teachingPurpose": "通过一级模拟软件练习，巩固知识，解决知识难点，熟悉考试环境。",
    "knowledgeGoals": "1、计算机基础知识理论题 2、文件或文件夹的管理 3、上网（电子邮件收发）4、字处理 5、电子表格 6、演示文稿",
    "abilityGoals": "1、Win 10基本操作 2、上网，按要求完成操作 3、字处理的基本操作 4、电子表格的基本操作 5、演示文稿的基本操作",
    "qualityGoals": "1、培养学生细心解题的科学态度。2、培养学生探索知识的精神。",
    "keyPoints": "1、字处理的基本操作 2、电子表格的基本操作 3、演示文稿的基本操作",
}

KNOWLEDGE_A = """1、选择题（计算机基础知识和网络的基本知识）（20分）
2、Windows操作系统的使用。（10分）
3、浏览器（IE）的简单使用和电子邮件收发（10分）
4、字处理 Word操作（25分）：查找替换、格式替换、文字水印、文字边框渐变、字符格式、段落格式、分栏、超链接、插入表格、表格对齐、行高、表框RGB、表标题、边框、重复标题行
5、电子表格 Excel操作（20分）：合并单元格、公式计算、百分比格式、IF函数、图表、重命名工作表、自动筛选
6、演示文稿 PowerPoint操作（15分）：应用主题、幻灯片切换、放映方式、版式、插入图片、动画、插入表格、移动/删除幻灯片"""

KNOWLEDGE_B = """1、选择题（计算机基础知识和网络的基本知识）（20分）
2、Windows操作系统的使用。（10分）
3、浏览器（IE）的简单使用和电子邮件收发（10分）
4、字处理 Word操作（25分）：查找替换、页面设置、文字效果映像、双波浪下划线、段落格式、分栏、页面颜色、文字转表格、排序、脚注、行高列宽、表格样式、边框底纹
5、电子表格 Excel操作（20分）：重命名、智能填充、合并单元格、对齐、货币格式、边框底纹、IF函数、SUM、公式、图表、多关键字排序、高级筛选
6、演示文稿 PowerPoint操作（15分）：插入新幻灯片、动画、设计模板、插入图片、字体颜色与行距、背景、移动幻灯片、更换版式、SmartArt、幻灯片切换"""


def empty_flow() -> dict[str, str]:
    return {k: "" for k in list(ACTIVITY_FLOW_LABELS)}


def empty_plan() -> dict[str, Any]:
    return {
        "school": SCHOOL_DEFAULTS["school"],
        "academicYear": "2024-2025",
        "semester": 2,
        "course": SCHOOL_DEFAULTS["course"],
        "planNumber": "",
        "teachingGroup": SCHOOL_DEFAULTS["teachingGroup"],
        "teacher": "",
        "teachingObject": "",
        "teachDate": "",
        "week": 1,
        "session": 1,
        "contentTitle": "",
        "contentDetail": "",
        "plannedHours": 2,
        "teachingPurpose": "",
        "knowledgeGoals": "",
        "abilityGoals": "",
        "qualityGoals": "",
        "keyPoints": "",
        "teachingMethods": SCHOOL_DEFAULTS["teachingMethods"],
        "teachingResources": SCHOOL_DEFAULTS["teachingResources"],
        "activityFlow": empty_flow(),
    }


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return True
    return str(value).strip() != ""


def validate_plan(data: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if not isinstance(data, dict):
        return {"ok": False, "issues": [{"path": "(root)", "message": "教案必须是 JSON 对象"}]}

    for key in REQUIRED_TOP:
        if key not in data or not _nonempty(data.get(key)):
            issues.append({"path": key, "message": f"{key} 不能为空"})

    week = data.get("week")
    session = data.get("session")
    if not isinstance(week, int) or week <= 0:
        issues.append({"path": "week", "message": "周次须为正整数"})
    if not isinstance(session, int) or session <= 0:
        issues.append({"path": "session", "message": "课次须为正整数"})

    sem = data.get("semester")
    if sem not in (1, 2):
        issues.append({"path": "semester", "message": "学期须为 1 或 2"})

    hours = data.get("plannedHours")
    if not isinstance(hours, (int, float)) or hours <= 0:
        issues.append({"path": "plannedHours", "message": "计划学时须为正数"})

    flow = data.get("activityFlow")
    if not isinstance(flow, dict):
        issues.append({"path": "activityFlow", "message": "教学活动流程必须是对象"})
    else:
        for key in REQUIRED_FLOW:
            if not _nonempty(flow.get(key)):
                label = ACTIVITY_FLOW_LABELS.get(key, key)
                issues.append({"path": f"activityFlow.{key}", "message": f"{label} 不能为空"})
        task = str(flow.get("taskImplementation") or "")
        if task and ("必须完成" not in task and "必做" not in task):
            issues.append(
                {
                    "path": "activityFlow.taskImplementation",
                    "message": "工作任务实施建议包含「必须完成/必做」任务说明",
                }
            )

    return {"ok": len(issues) == 0, "issues": issues, "plan": data if not issues else None}


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
        "taskImplementation": f"1、必须完成：完成{must}\n2、选做：{opt}",
        "assessment": "1、过程考核：30\n2、结果考核：70",
        "summary": "评讲课堂学生遇到的难题",
        "homework": "课后复习选择题",
        "reflection": "课后根据课堂完成情况补充教学反思。",
    }
    return plan


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_examples() -> list[tuple[Path, dict[str, Any]]]:
    items: list[tuple[Path, dict[str, Any]]] = []
    if not EXAMPLES_DIR.is_dir():
        return items
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        items.append((path, load_json(path)))
    return items


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


def score_against_examples(plan: dict[str, Any]) -> dict[str, Any]:
    checks = [
        ("has_meta", 10, bool(plan.get("academicYear") and plan.get("course") and plan.get("week") and plan.get("session"))),
        ("has_content", 10, bool(str(plan.get("contentTitle") or "").strip())),
        ("has_purpose", 10, bool(str(plan.get("teachingPurpose") or "").strip())),
        ("has_knowledge_goals", 10, bool(str(plan.get("knowledgeGoals") or "").strip())),
        ("has_ability_goals", 10, bool(str(plan.get("abilityGoals") or "").strip())),
        ("has_quality_goals", 10, bool(str(plan.get("qualityGoals") or "").strip())),
        ("has_keypoints", 10, bool(str(plan.get("keyPoints") or "").strip())),
        ("has_methods_resources", 10, bool(plan.get("teachingMethods") and plan.get("teachingResources"))),
        (
            "has_eight_steps",
            15,
            isinstance(plan.get("activityFlow"), dict)
            and all(str(plan["activityFlow"].get(k) or "").strip() for k in REQUIRED_FLOW),
        ),
        ("passes_validate", 5, validate_plan(plan)["ok"]),
    ]
    score = sum(w for _, w, ok in checks if ok)
    max_score = sum(w for _, w, _ in checks)
    nearest = None
    samples = load_examples()
    if samples:
        best_id, best_ov = "", -1.0
        flow = plan.get("activityFlow") or {}
        for path, sample in samples:
            ident = f"{sample.get('contentTitle')}-W{sample.get('week')}S{sample.get('session')}"
            ov = overlap_ratio(str(plan.get("contentTitle") or ""), str(sample.get("contentTitle") or "")) * 0.3
            ov += overlap_ratio(
                str(flow.get("knowledgeLearning") or ""),
                str((sample.get("activityFlow") or {}).get("knowledgeLearning") or ""),
            ) * 0.7
            if ov > best_ov:
                best_id, best_ov = ident, ov
        nearest = {"id": best_id, "overlap": round(best_ov, 4), "file": samples[0][0].name if samples else ""}
        # keep file of best
        for path, sample in samples:
            ident = f"{sample.get('contentTitle')}-W{sample.get('week')}S{sample.get('session')}"
            if ident == best_id:
                nearest["file"] = path.name
                break
    return {
        "score": score,
        "maxScore": max_score,
        "ratio": round(score / max_score, 4) if max_score else 0,
        "checks": [{"id": i, "weight": w, "passed": ok} for i, w, ok in checks],
        "nearestSample": nearest,
    }


def dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
