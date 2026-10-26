# -*- coding: utf-8 -*-
"""教案 MCP：stdio JSON-RPC，工具实现复用技能 scripts/lib.py。

工具边界：参数按 inputSchema 校验，单个请求失败只返回结构化错误，不终止服务。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import skill_scripts

sys.path.insert(0, str(skill_scripts()))
from export_docx import export_docx  # type: ignore
from lib import (  # type: ignore
    adversarial_review,
    draft_plan,
    dump,
    empty_plan,
    export_gate,
    record_teacher_override,
    score_against_examples,
    validate_plan,
)

SERVER_INFO = {"name": "lesson-plan-design", "version": "1.0.0"}

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

TYPE_LABELS = {
    "object": "对象",
    "integer": "整数",
    "number": "数字",
    "string": "字符串",
    "boolean": "布尔值",
    "array": "数组",
}


def _jsonrpc_error(mid, code: int, message: str, data: dict | None = None) -> dict:
    error: dict = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": mid, "error": error}


def _type_ok(value, expected: str | None) -> bool:
    if expected is None:
        return True
    if expected == "object":
        return isinstance(value, dict)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    return True


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
        "description": "校验教案是否满足校标结构",
        "inputSchema": {
            "type": "object",
            "required": ["plan"],
            "properties": {"plan": {"type": "object"}},
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
                "reviewerMode": {"type": "string", "enum": ["native_subagent", "role_simulation"]},
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
        "description": "记录教师对当前 blocker 或 major 问题的实名放行",
        "inputSchema": {
            "type": "object",
            "required": ["plan", "reviewReport", "issueId", "teacher", "reason"],
            "properties": {
                "plan": {"type": "object"},
                "reviewReport": {"type": "object"}, "issueId": {"type": "string"},
                "teacher": {"type": "string"}, "reason": {"type": "string"},
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


def _result(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def _dispatch_tool(name: str, args: dict) -> dict:
    if not isinstance(args, dict):
        return _result(dump({"ok": False, "error": "工具参数必须是 JSON 对象"}))
    if name == "get_lesson_template":
        return _result(dump({"skeleton": empty_plan()}))
    if name == "draft_lesson_plan":
        plan = draft_plan(
            int(args["week"]),
            int(args["session"]),
            str(args["contentTitle"]),
            content_detail=str(args.get("contentDetail") or ""),
            planned_hours=float(args.get("plannedHours") or 2),
            teacher=str(args.get("teacher") or ""),
            teaching_object=str(args.get("teachingObject") or ""),
        )
        return _result(dump({"plan": plan, "validation": validate_plan(plan)}))
    if name == "validate_lesson_plan":
        return _result(dump(validate_plan(args.get("plan") or args)))
    if name == "start_adversarial_review":
        plan = args.get("plan") or args
        try:
            report = adversarial_review(
                plan,
                round_number=int(args.get("round") or 1),
                finding=args.get("finding"),
                reviewer=str(args.get("reviewerMode") or "role_simulation"),
                previous_report=args.get("previousReport"),
                no_counterexample=bool(args.get("noCounterexample")),
            )
        except (TypeError, ValueError) as exc:
            return _result(dump({"ok": False, "error": str(exc)}))
        return _result(dump(report))
    if name == "read_lesson_review":
        plan = args.get("plan") or {}
        report = args.get("reviewReport")
        gate = export_gate(plan, report)
        return _result(dump({"report": report, "valid": gate["ok"], "gate": gate}))
    if name == "record_teacher_override":
        report = args.get("reviewReport") or {}
        try:
            override = record_teacher_override(
                report, str(args.get("issueId") or ""),
                teacher=str(args.get("teacher") or ""),
                reason=str(args.get("reason") or ""),
                plan=args.get("plan") or {},
            )
        except (TypeError, ValueError, AttributeError) as exc:
            return _result(dump({"ok": False, "error": str(exc)}))
        return _result(dump({"ok": True, "override": override, "reviewReport": report}))
    if name == "export_lesson_docx":
        plan = args.get("plan") or args
        gate = export_gate(plan, args.get("reviewReport"))
        if not gate["ok"]:
            return _result(dump({"ok": False, "reasons": gate["reasons"]}))
        out = Path(args.get("outputPath") or f"教案_第{plan.get('week')}周第{plan.get('session')}次.docx")
        base_dir = Path(str(args["baseDir"])) if args.get("baseDir") else out.parent
        saved = export_docx(plan, out, base_dir=base_dir)
        return _result(dump({"ok": True, "path": str(saved), "bytes": saved.stat().st_size}))
    if name == "score_against_samples":
        return _result(dump(score_against_examples(args.get("plan") or args)))
    return _result(json.dumps({"error": f"unknown tool {name}"}))


def call_tool(name: str, args: dict) -> dict:
    try:
        return _dispatch_tool(name, args)
    except Exception as exc:  # noqa: BLE001 - 工具边界必须兜底，服务不能退出
        return _result(
            dump({"ok": False, "error": {"code": "TOOL_ERROR", "message": str(exc)}})
        )


def handle(msg: dict) -> dict | None:
    if not isinstance(msg, dict):
        return _jsonrpc_error(
            None,
            INVALID_REQUEST,
            "请求必须是 JSON 对象",
            {"code": "INVALID_REQUEST", "message": "请求必须是 JSON 对象"},
        )
    mid = msg.get("id")
    method = msg.get("method")
    if not isinstance(method, str) or not method:
        return _jsonrpc_error(
            mid,
            INVALID_REQUEST,
            "缺少 method",
            {"code": "INVALID_REQUEST", "message": "缺少 method"},
        )
    if method == "initialize":
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }
    if method == "notifications/initialized" or method == "initialized":
        return None
    if method.startswith("notifications/"):
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
        name = params.get("name")
        args = params.get("arguments") or {}
        tool = next((item for item in TOOLS if item.get("name") == name), None)
        if tool is None:
            return _jsonrpc_error(
                mid,
                METHOD_NOT_FOUND,
                "未知工具",
                {"code": "METHOD_NOT_FOUND", "message": f"未知工具：{name}"},
            )
        errors = _validate_tool_arguments(tool, args)
        if errors:
            return _jsonrpc_error(
                mid,
                INVALID_PARAMS,
                "工具参数不合法",
                {"code": "INVALID_PARAMS", "message": "工具参数不合法", "details": errors},
            )
        try:
            result = _dispatch_tool(name, args)
        except Exception as exc:  # noqa: BLE001 - 单个工具失败不得终止 stdio 服务
            return _jsonrpc_error(
                mid,
                INTERNAL_ERROR,
                "工具执行失败",
                {"code": "TOOL_ERROR", "message": str(exc)},
            )
        return {"jsonrpc": "2.0", "id": mid, "result": result}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    return _jsonrpc_error(
        mid,
        METHOD_NOT_FOUND,
        "未知方法",
        {"code": "METHOD_NOT_FOUND", "message": f"未知方法：{method}"},
    )


def _write(reply: dict) -> None:
    sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            _write(
                _jsonrpc_error(
                    None,
                    PARSE_ERROR,
                    "JSON 解析失败",
                    {"code": "PARSE_ERROR", "message": str(exc)},
                )
            )
            continue
        try:
            reply = handle(msg)
        except Exception as exc:  # noqa: BLE001 - 保持 stdio 服务存活
            mid = msg.get("id") if isinstance(msg, dict) else None
            reply = _jsonrpc_error(
                mid,
                INTERNAL_ERROR,
                "内部错误",
                {"code": "TOOL_ERROR", "message": str(exc)},
            )
        if reply is not None:
            _write(reply)


if __name__ == "__main__":
    main()
