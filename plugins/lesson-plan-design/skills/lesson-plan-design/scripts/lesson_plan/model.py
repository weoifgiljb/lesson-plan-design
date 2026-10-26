# -*- coding: utf-8 -*-
"""领域模型：常量、空教案、哈希与共享纯函数。"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parents[2]
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
def plan_hash(plan: dict[str, Any]) -> str:
    """Return a stable content hash used to invalidate stale review evidence."""
    encoded = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
