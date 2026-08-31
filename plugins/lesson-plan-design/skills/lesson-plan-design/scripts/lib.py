# -*- coding: utf-8 -*-
"""校标教案共享逻辑：schema、草稿、校验、评分。仅标准库。"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = SKILL_DIR / "examples"
TEMPLATES_DIR = SKILL_DIR / "templates"
REVIEW_SCHEMA_VERSION = 1
RUBRIC_VERSION = "1.0"
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
    key = f"{hypothesis}:{'|'.join(affected_paths)}".encode("utf-8")
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
    required = ("severity", "hypothesis", "evidence", "affectedPaths", "whyItBreaksTheLoop", "minimalRepair")
    missing = [key for key in required if not finding.get(key)]
    if missing:
        raise ValueError(f"审查发现缺少字段：{', '.join(missing)}")
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
    assessment = str(flow.get("assessment") or "").strip()
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
) -> dict[str, Any]:
    """Build one immutable review round; no mutation of the lesson plan occurs here."""
    structural = validate_plan(plan)
    report: dict[str, Any] = {
        "schemaVersion": REVIEW_SCHEMA_VERSION,
        "rubricVersion": RUBRIC_VERSION,
        "planHash": plan_hash(plan),
        "round": round_number,
        "reviewer": reviewer,
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
        "structuralValidation": {key: value for key, value in structural.items() if key != "plan"},
        "findings": [],
        "overrides": [],
        "repairHistory": [],
    }
    if previous_report:
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

    strongest = _normalise_finding(plan, finding, round_number) if finding else _preflight_adversarial_finding(plan, round_number)
    if strongest:
        report["findings"] = [strongest]
        report["status"] = "needs_repair"
        report["conclusion"] = "发现一个需独立修复 Agent 处理的最强反例。"
    else:
        report["status"] = "passed"
        report["conclusion"] = "本轮未能证明教学闭环失效。"
    return report


def record_teacher_override(report: dict[str, Any], finding_id: str, *, teacher: str, reason: str) -> dict[str, Any]:
    if not teacher.strip() or not reason.strip():
        raise ValueError("教师姓名和放行原因不能为空")
    finding = next((item for item in report.get("findings", []) if item.get("id") == finding_id), None)
    if not finding:
        raise ValueError(f"未找到审查问题：{finding_id}")
    if finding.get("severity") not in BLOCKING_SEVERITIES:
        raise ValueError("仅 blocker 或 major 问题需要教师放行")
    override = {
        "findingId": finding_id,
        "teacher": teacher.strip(),
        "reason": reason.strip(),
        "planHash": report.get("planHash"),
        "approvedAt": datetime.now(timezone.utc).isoformat(),
    }
    report.setdefault("overrides", []).append(override)
    finding["status"] = "waived"
    return override


def export_gate(plan: dict[str, Any], report: dict[str, Any] | None) -> dict[str, Any]:
    structural = validate_plan(plan)
    reasons: list[str] = []
    if not structural["ok"]:
        reasons.append("教案未通过结构校验")
    if not report:
        reasons.append("缺少当前教案的对抗审查报告")
        return {"ok": False, "reasons": reasons, "structuralValidation": structural}
    required_report = ("schemaVersion", "rubricVersion", "planHash", "round", "reviewer", "reviewedAt", "structuralValidation", "findings", "overrides", "repairHistory", "status")
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
    if not isinstance(report.get("structuralValidation"), dict) or not report["structuralValidation"].get("ok"):
        reasons.append("审查报告显示结构校验未通过")
    report_status = report.get("status")
    if report_status not in {"passed", "needs_repair", "structure_invalid"}:
        reasons.append("审查报告状态无效")
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    has_open_blocking_finding = False
    for item in findings:
        if not isinstance(item, dict):
            reasons.append("审查问题格式无效")
            continue
        severity = item.get("severity")
        status = item.get("status")
        if severity not in {"blocker", "major", "minor"}:
            reasons.append("审查问题严重级别无效")
        if status not in {"open", "waived"}:
            reasons.append("审查问题状态无效")
        if severity in BLOCKING_SEVERITIES and status == "open":
            has_open_blocking_finding = True
    if report_status == "passed" and findings:
        reasons.append("通过的审查报告不能包含问题")
    if report_status == "needs_repair" and not any(
        item.get("severity") in BLOCKING_SEVERITIES for item in findings if isinstance(item, dict)
    ):
        reasons.append("待修复的审查报告缺少未关闭的 blocker 或 major 问题")
    if report_status == "structure_invalid" and not reasons:
        reasons.append("审查报告状态显示结构校验未通过")
    approved_ids = {
        item.get("findingId")
        for item in report.get("overrides", [])
        if item.get("planHash") == plan_hash(plan) and item.get("teacher") and item.get("reason")
    }
    for item in findings:
        if item.get("severity") in BLOCKING_SEVERITIES and item.get("status") == "open" and item.get("id") not in approved_ids:
            reasons.append(f"存在未关闭的 {item.get('severity')} 问题：{item.get('id')}")
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
