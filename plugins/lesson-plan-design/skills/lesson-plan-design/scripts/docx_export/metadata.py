# -*- coding: utf-8 -*-
"""DOCX 元信息与学时格式。"""
from __future__ import annotations


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
    missing: list[str] = []
    for key, label in (
        ("teacher", "任课教师"),
        ("teachingObject", "教学对象"),
        ("teachDate", "授课日期"),
    ):
        if not str(plan.get(key) or "").strip():
            missing.append(label)
    return missing


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

