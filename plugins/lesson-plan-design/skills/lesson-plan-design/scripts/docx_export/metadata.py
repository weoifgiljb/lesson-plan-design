# -*- coding: utf-8 -*-
"""DOCX 元信息与学时格式。"""
from __future__ import annotations

from lesson_plan.model import missing_metadata


def _meta_value(value, placeholder: str = "____") -> str:
    text = str(value or "").strip()
    return text or placeholder


def _format_hours(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _meta_value(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:g}"


def _missing_metadata(plan: dict) -> list[str]:
    return missing_metadata(plan)


def _meta_line(plan: dict, independence: str | None = None) -> str:
    suffix = ""
    if independence == "role_simulation":
        suffix = "  审校方式：角色模拟"
    elif independence == "human":
        suffix = "  审校方式：人工审校"
    return (
        f"学校：{_meta_value(plan.get('school'))}  "
        f"编号：{_meta_value(plan.get('planNumber'))}  "
        f"{plan.get('academicYear', '')}学年 第{plan.get('semester', '')}学期  "
        f"课程：{plan.get('course', '')}  教研组：{plan.get('teachingGroup', '')}  "
        f"任课教师：{_meta_value(plan.get('teacher'))}  "
        f"教学对象：{_meta_value(plan.get('teachingObject'))}  "
        f"授课日期：{_meta_value(plan.get('teachDate'))}  "
        f"第{plan.get('week')}周第{plan.get('session')}次"
    ) + suffix


def _override_line(overrides: list[dict] | None) -> str:
    """把教师放行/接受轻微问题记录写进 Word，保证纸面可追溯。"""
    entries: list[str] = []
    for item in overrides or []:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind") or "teacher_override"
        label = "接受轻微问题" if kind == "minor_acceptance" else "教师放行"
        finding = str(item.get("findingId") or "").strip()
        teacher = str(item.get("teacher") or "").strip()
        reason = str(item.get("reason") or "").strip()
        approved = str(item.get("approvedAt") or "").strip().replace("T", " ")[:16]
        if not (finding and teacher and reason):
            continue
        entries.append(f"{label}：{finding} · {teacher} · {approved} · {reason}")
    return "  ".join(entries)

