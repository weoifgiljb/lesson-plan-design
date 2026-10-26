# -*- coding: utf-8 -*-
"""校标教案共享逻辑：schema、草稿、校验、评分。仅标准库。"""
from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = SKILL_DIR / "examples"
EXAMPLES_INDEX = EXAMPLES_DIR / "index.json"
TEMPLATES_DIR = SKILL_DIR / "templates"
C_LANGUAGE_TEMPLATES_PATH = TEMPLATES_DIR / "c-language-topics.json"
REVIEW_SCHEMA_VERSION = 1
RUBRIC_VERSION = "1.0"
RULES_VERSION = "1.1.0"
TOOL_VERSION = "1.0.0"
MIN_OVERRIDE_REASON = 6
BLOCKING_SEVERITIES = {"blocker", "major"}

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
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return str(value).strip() != ""


def _structured_activities(value: Any) -> list[dict[str, Any]] | None:
    """Return structured activity rows, accepting a single object or list."""
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    return None


def _normalise_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _finalize_findings(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for item in items:
        key = (str(item.get("path", "")), str(item.get("message", "")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return sorted(unique, key=lambda item: (item.get("path", ""), item.get("message", "")))


def _structured_task_text(rows: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for row in rows:
        for key in ("mainContent", "teacherActivity", "studentActivity", "evidence"):
            value = row.get(key)
            if value:
                parts.append(str(value))
    return "\n".join(parts)


def _activity_minutes(flow: dict[str, Any]) -> tuple[float, bool, bool]:
    total = 0.0
    found = False
    missing = False
    for value in flow.values():
        rows = _structured_activities(value)
        if rows is None:
            continue
        for row in rows:
            minutes = row.get("minutes")
            if minutes is None:
                missing = True
                continue
            if isinstance(minutes, bool) or not isinstance(minutes, (int, float)):
                continue
            total += float(minutes)
            found = True
    return total, found, missing


def _catalog_conflicts(data: dict[str, Any]) -> list[dict[str, str]]:
    course = _normalise_text(data.get("course"))
    week = data.get("week")
    session = data.get("session")
    if not course or type(week) is not int or type(session) is not int:
        return []
    if week <= 0 or session <= 0:
        return []
    try:
        samples = load_examples()
    except (OSError, json.JSONDecodeError):
        return []
    entry: dict[str, Any] | None = None
    for _path, sample in samples:
        if _normalise_text(sample.get("course")) != course:
            continue
        if sample.get("week") == week and sample.get("session") == session:
            entry = sample
            break
    if entry is None:
        return []
    findings: list[dict[str, str]] = []
    title = _normalise_text(data.get("contentTitle"))
    catalog_title = _normalise_text(entry.get("contentTitle"))
    if title and catalog_title and title != catalog_title:
        findings.append(
            {
                "path": "contentTitle",
                "message": f"与样例目录第 {week} 周第 {session} 次的课题不一致（目录：{entry.get('contentTitle')}）",
            }
        )
    detail = _normalise_text(data.get("contentDetail"))
    catalog_detail = _normalise_text(entry.get("contentDetail"))
    if detail and catalog_detail and detail != catalog_detail:
        findings.append(
            {
                "path": "contentDetail",
                "message": f"与样例目录第 {week} 周第 {session} 次的练习套别不一致（目录：{entry.get('contentDetail')}）",
            }
        )
    return findings


def _validate_activity_rows(value: Any, path: str, issues: list[dict[str, str]]) -> None:
    rows = _structured_activities(value)
    if rows is None:
        return
    if not rows:
        issues.append({"path": path, "message": "结构化活动列表不能为空"})
        return
    for idx, row in enumerate(rows):
        row_path = f"{path}[{idx}]"
        if not _nonempty(row.get("mainContent")):
            issues.append({"path": f"{row_path}.mainContent", "message": "主要内容不能为空"})
        minutes = row.get("minutes")
        if minutes is not None and (
            isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or minutes < 0
        ):
            issues.append({"path": f"{row_path}.minutes", "message": "分钟数须为非负数字"})
        # Teacher/student/evidence are optional individually for compatibility;
        # at least one learner-facing action or verifiable output is recommended.


def validate_plan(
    data: Any,
    *,
    strict: bool = False,
    minutes_tolerance: float = 0.0,
) -> dict[str, Any]:
    warnings: list[dict[str, str]] = []
    if not isinstance(data, dict):
        return {
            "ok": False,
            "issues": [{"path": "(root)", "message": "教案必须是 JSON 对象"}],
            "warnings": [],
            "ruleVersion": RULES_VERSION,
        }

    issues: list[dict[str, str]] = []
    for key in REQUIRED_TOP:
        if key not in data or not _nonempty(data.get(key)):
            issues.append({"path": key, "message": f"{key} 不能为空"})

    week = data.get("week")
    session = data.get("session")
    if "week" in data and _nonempty(week):
        if type(week) is not int or week <= 0:
            issues.append({"path": "week", "message": "周次须为正整数"})
    if "session" in data and _nonempty(session):
        if type(session) is not int or session <= 0:
            issues.append({"path": "session", "message": "课次须为正整数"})

    sem = data.get("semester")
    if "semester" in data and _nonempty(sem):
        if type(sem) is not int or sem not in (1, 2):
            issues.append({"path": "semester", "message": "学期须为 1 或 2"})

    hours = data.get("plannedHours")
    if "plannedHours" in data and _nonempty(hours):
        if isinstance(hours, bool) or not isinstance(hours, (int, float)) or hours <= 0:
            issues.append({"path": "plannedHours", "message": "计划学时须为正数"})

    flow = data.get("activityFlow")
    if not isinstance(flow, dict):
        issues.append({"path": "activityFlow", "message": "教学活动流程必须是对象"})
    else:
        for key in REQUIRED_FLOW:
            if not _nonempty(flow.get(key)):
                label = ACTIVITY_FLOW_LABELS.get(key, key)
                issues.append({"path": f"activityFlow.{key}", "message": f"{label} 不能为空"})
            _validate_activity_rows(flow.get(key), f"activityFlow.{key}", issues)
        task_value = flow.get("taskImplementation")
        task_rows = _structured_activities(task_value)
        task_text = _structured_task_text(task_rows) if task_rows is not None else str(task_value or "")
        if task_text and ("必须完成" not in task_text and "必做" not in task_text):
            issues.append(
                {
                    "path": "activityFlow.taskImplementation",
                    "message": "工作任务实施须包含「必须完成」或「必做」任务说明",
                }
            )

    try:
        tolerance = max(0.0, float(minutes_tolerance))
    except (TypeError, ValueError):
        tolerance = 0.0
    if isinstance(flow, dict) and isinstance(hours, (int, float)) and not isinstance(hours, bool) and hours > 0:
        total, found, missing = _activity_minutes(flow)
        if missing:
            warnings.append(
                {"path": "activityFlow", "message": "部分活动未填写分钟数，无法核对合计"}
            )
        if found:
            expected = float(hours) * 45
            if abs(total - expected) > tolerance + 1e-9:
                issues.append(
                    {
                        "path": "activityFlow",
                        "message": f"活动分钟合计 {total:g} 与计划学时 {hours:g}（{expected:g} 分钟）不一致",
                    }
                )

    conflicts = _catalog_conflicts(data)
    if strict:
        issues.extend(conflicts)
    else:
        warnings.extend(conflicts)

    issues = _finalize_findings(issues)
    warnings = _finalize_findings(warnings)
    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "ruleVersion": RULES_VERSION,
        "plan": data if not issues else None,
    }


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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_examples() -> list[tuple[Path, dict[str, Any]]]:
    items: list[tuple[Path, dict[str, Any]]] = []
    if not EXAMPLES_DIR.is_dir():
        return items
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        items.append((path, load_json(path)))
    return items


def example_entries(directory: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    root = Path(directory) if directory is not None else EXAMPLES_DIR
    index_path = root / "index.json"
    index = load_json(index_path) if index_path.is_file() else {"examples": []}
    indexed = {
        str(item.get("file")): item
        for item in index.get("examples", [])
        if isinstance(item, dict) and item.get("file")
    }
    entries: list[dict[str, Any]] = []
    files: set[str] = set()
    for path in sorted(root.glob("*.json")):
        if path.name == "index.json":
            continue
        plan = load_json(path)
        expected = indexed.get(path.name)
        entries.append({
            "file": path.name,
            "plan": plan,
            "index": expected,
            "stale": expected is None or expected.get("planHash") != plan_hash(plan),
        })
        files.add(path.name)
    return entries, sorted(set(indexed) - files)


def check_examples(directory: Path | None = None) -> dict[str, Any]:
    entries, extra = example_entries(directory)
    errors: list[str] = []
    stale: list[str] = []
    missing: list[str] = []
    fields = ("course", "week", "session", "contentTitle")
    for entry in entries:
        name = entry["file"]
        if entry["index"] is None:
            missing.append(name)
            errors.append(f"index.json 缺少样例：{name}")
            continue
        if entry["stale"]:
            stale.append(name)
            errors.append(f"样例哈希已过期：{name}")
            continue
        for field in fields:
            if entry["index"].get(field) != entry["plan"].get(field):
                errors.append(f"样例元信息不一致：{name} 的 {field}")
    for name in extra:
        errors.append(f"index.json 引用了不存在的样例：{name}")
    return {
        "ok": not errors,
        "count": len(entries),
        "errors": errors,
        "stale": stale,
        "missing": missing,
        "extra": extra,
    }


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


def plan_hash(plan: dict[str, Any]) -> str:
    """Return a stable content hash used to invalidate stale review evidence."""
    encoded = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
