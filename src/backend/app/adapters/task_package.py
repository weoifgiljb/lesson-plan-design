# -*- coding: utf-8 -*-
"""任务包内容：task.json + 教案模板 + 字段说明（ZIP 由 archive 适配层生成）。"""
from __future__ import annotations

import json
from typing import Any

from app.adapters import archive


def build(task: dict[str, Any], sample_plan: dict[str, Any] | None, sample_id: int | None) -> bytes:
    template = _template(task, sample_plan)
    task_meta = {
        "taskId": int(task["id"]),
        "course": task["course"],
        "week": int(task["week"]),
        "session": int(task["session"]),
        "title": task["title"],
        "className": task["class_name"],
        "dueDate": task["due_date"],
        "status": task["status"],
        "sampleId": sample_id,
    }
    return archive.build_zip(
        {
            "task.json": json.dumps(task_meta, ensure_ascii=False, indent=2).encode("utf-8"),
            "plan.template.json": json.dumps(template, ensure_ascii=False, indent=2).encode("utf-8"),
            "README.md": _readme(task, sample_id).encode("utf-8"),
        }
    )


def _template(task: dict[str, Any], sample_plan: dict[str, Any] | None) -> dict[str, Any]:
    if sample_plan:
        template = json.loads(json.dumps(sample_plan))
    else:
        template = {
            "schemaVersion": 1,
            "course": "",
            "week": 0,
            "session": 0,
            "contentTitle": "",
            "activityFlow": {},
        }
    template["course"] = task["course"]
    template["week"] = int(task["week"])
    template["session"] = int(task["session"])
    template["contentTitle"] = task["title"]
    return template


def _readme(task: dict[str, Any], sample_id: int | None) -> str:
    sample = (
        f"- 最近样例：GET /api/v1/samples?course={task['course']}&week={task['week']}&session={task['session']}"
        if sample_id is None
        else f"- 最近样例：sampleId={sample_id}"
    )
    return "\n".join(
        [
            f"# 教学任务：{task['course']} 第 {task['week']} 周第 {task['session']} 次",
            "",
            f"- 课题：{task['title']}",
            f"- 班级：{task['class_name'] or '未指定'}",
            f"- 截止时间：{task['due_date'] or '未设置'}",
            sample,
            "",
            "## 使用方式",
            "1. 在插件端打开 plan.template.json，补齐教案字段并完成审查。",
            "2. 用契约包（manifest.json + plan.json + plan.review.json）上传平台。",
            "3. 上传后任务状态会随入库、审查、导出自动推进。",
            "",
            "## 字段说明",
            "- course/week/session/contentTitle：任务身份，必须与任务一致。",
            "- activityFlow：八步教学流程，按插件端 schema 填写。",
            "- 其余字段：见插件端 references/schema.md。",
        ]
    )
