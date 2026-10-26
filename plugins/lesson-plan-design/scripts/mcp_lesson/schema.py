# -*- coding: utf-8 -*-
"""MCP 工具 schema 与参数类型校验。"""
from __future__ import annotations

SERVER_INFO = {"name": "lesson-plan-design", "version": "1.0.0"}

TYPE_LABELS = {
    "object": "对象",
    "integer": "整数",
    "number": "数字",
    "string": "字符串",
    "boolean": "布尔值",
    "array": "数组",
}

def _always_true(value) -> bool:
    return True


def _is_object(value) -> bool:
    return isinstance(value, dict)


def _is_integer(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_string(value) -> bool:
    return isinstance(value, str)


def _is_boolean(value) -> bool:
    return isinstance(value, bool)


def _is_array(value) -> bool:
    return isinstance(value, list)


TYPE_CHECKS = {
    "object": _is_object,
    "integer": _is_integer,
    "number": _is_number,
    "string": _is_string,
    "boolean": _is_boolean,
    "array": _is_array,
}

def _type_ok(value, expected: str | None) -> bool:
    return TYPE_CHECKS.get(expected, _always_true)(value)


def _validate_tool_arguments(tool: dict, args: dict) -> list[dict[str, str]]:
    schema = tool.get("inputSchema") or {}
    errors: list[dict[str, str]] = []
    if not isinstance(args, dict):
        return [{"path": "arguments", "message": "工具参数必须是 JSON 对象"}]
    for name in schema.get("required", []):
        if name not in args:
            errors.append({"path": name, "message": f"缺少必填参数：{name}"})
    for name, spec in (schema.get("properties") or {}).items():
        if name not in args or not isinstance(spec, dict):
            continue
        expected = spec.get("type")
        if not _type_ok(args[name], expected):
            errors.append(
                {
                    "path": name,
                    "message": f"参数 {name} 须为{TYPE_LABELS.get(expected, expected)}",
                }
            )
        enum = spec.get("enum")
        if enum and args[name] not in enum:
            options = "、".join(str(item) for item in enum)
            errors.append({"path": name, "message": f"参数 {name} 须为 {options}"})
    return errors

TOOLS = [
    {
        "name": "get_lesson_template",
        "description": "获取东莞经贸学校信息技术教案空骨架",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "draft_lesson_plan",
        "description": "按周次/课次/课题草稿完整教案",
        "inputSchema": {
            "type": "object",
            "required": ["week", "session", "contentTitle"],
            "properties": {
                "week": {"type": "integer"},
                "session": {"type": "integer"},
                "contentTitle": {"type": "string"},
                "contentDetail": {"type": "string"},
                "plannedHours": {"type": "number"},
                "teacher": {"type": "string"},
                "teachingObject": {"type": "string"},
            },
        },
    },
    {
        "name": "validate_lesson_plan",
        "description": "校验教案是否满足校标结构；strict 时目录课题/套别冲突按错误处理",
        "inputSchema": {
            "type": "object",
            "required": ["plan"],
            "properties": {
                "plan": {"type": "object"},
                "strict": {"type": "boolean"},
                "minutesTolerance": {"type": "number"},
            },
        },
    },
    {
        "name": "start_adversarial_review",
        "description": "建立或完成本轮对抗审查报告；无反例时须传 noCounterexample=true，有反例时传 finding",
        "inputSchema": {
            "type": "object",
            "required": ["plan"],
            "properties": {
                "plan": {"type": "object"},
                "round": {"type": "integer"},
                "finding": {"type": "object"},
                "reviewerMode": {"type": "string", "enum": ["native_subagent", "role_simulation", "human"]},
                "previousReport": {"type": "object"},
                "noCounterexample": {"type": "boolean"},
            },
        },
    },
    {
        "name": "read_lesson_review",
        "description": "读取内存审查报告并验证其是否仍对应当前教案",
        "inputSchema": {
            "type": "object",
            "required": ["plan", "reviewReport"],
            "properties": {"plan": {"type": "object"}, "reviewReport": {"type": "object"}},
        },
    },
    {
        "name": "record_teacher_override",
        "description": "记录教师对 blocker/major 的实名放行，或对 minor 的实名接受",
        "inputSchema": {
            "type": "object",
            "required": ["plan", "reviewReport", "issueId", "teacher", "reason"],
            "properties": {
                "plan": {"type": "object"},
                "reviewReport": {"type": "object"}, "issueId": {"type": "string"},
                "teacher": {"type": "string"}, "reason": {"type": "string"},
                "strictTeacher": {"type": "boolean"},
            },
        },
    },
    {
        "name": "export_lesson_docx",
        "description": "仅在结构与当前对抗审查报告均放行时导出教案为 docx",
        "inputSchema": {
            "type": "object",
            "required": ["plan"],
            "properties": {
                "plan": {"type": "object"},
                "outputPath": {"type": "string"},
                "reviewReport": {"type": "object"},
                "baseDir": {"type": "string"},
                "strictIndependence": {"type": "boolean"},
                "strictMetadata": {"type": "boolean"},
            },
        },
    },
    {
        "name": "score_against_samples",
        "description": "对照 examples 金标准评分",
        "inputSchema": {
            "type": "object",
            "required": ["plan"],
            "properties": {"plan": {"type": "object"}},
        },
    },
]
