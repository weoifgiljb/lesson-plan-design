# -*- coding: utf-8 -*-
"""教案 MCP：stdio JSON-RPC，工具实现复用技能 scripts/lib.py。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import skill_scripts

sys.path.insert(0, str(skill_scripts()))
from export_docx import export_docx  # type: ignore
from lib import (  # type: ignore
    draft_plan,
    dump,
    empty_plan,
    score_against_examples,
    validate_plan,
)

SERVER_INFO = {"name": "lesson-plan-design", "version": "1.0.0"}

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
        "name": "export_lesson_docx",
        "description": "导出教案为 docx",
        "inputSchema": {
            "type": "object",
            "required": ["plan"],
            "properties": {
                "plan": {"type": "object"},
                "outputPath": {"type": "string"},
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


def call_tool(name: str, args: dict) -> dict:
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
    if name == "export_lesson_docx":
        plan = args.get("plan") or args
        check = validate_plan(plan)
        if not check["ok"]:
            return _result(dump(check))
        out = Path(args.get("outputPath") or f"教案_第{plan.get('week')}周第{plan.get('session')}次.docx")
        saved = export_docx(plan, out)
        return _result(dump({"ok": True, "path": str(saved), "bytes": saved.stat().st_size}))
    if name == "score_against_samples":
        return _result(dump(score_against_examples(args.get("plan") or args)))
    return _result(json.dumps({"error": f"unknown tool {name}"}))


def handle(msg: dict) -> dict | None:
    mid = msg.get("id")
    method = msg.get("method")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": msg.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }
    if method == "notifications/initialized" or method == "initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        return {"jsonrpc": "2.0", "id": mid, "result": call_tool(name, args)}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": method}}
    return None


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
