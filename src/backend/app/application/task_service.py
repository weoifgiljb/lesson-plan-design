# -*- coding: utf-8 -*-
"""任务编排：建课、列表、任务包与状态推进。"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from app.adapters import archive, storage, task_package
from app.adapters.db.repo import Repo
from app.application import audit_service
from app.domain import library, task_rules
from app.domain.errors import AppError


def create(
    repo: Repo, user: dict[str, Any], payload: dict[str, Any], *, ip: str = "", trace_id: str = ""
) -> dict[str, Any]:
    data = task_rules.validate(
        payload.get("course"), payload.get("week"), payload.get("session"),
        payload.get("title"), payload.get("className", ""),
    )
    if repo.find_task(data["course"], data["week"], data["session"], data["class_name"]):
        raise AppError("CONFLICT_STALE", "同一课程/周次/课次/班级的任务已存在")
    due = payload.get("dueDate")
    task_id = repo.insert_task(
        data["course"], data["week"], data["session"], data["title"], data["class_name"],
        int(user.get("id") or 0), due.isoformat() if due else None,
    )
    audit_service.record(
        repo, actor_id=int(user.get("id") or 0), action="task.create", target_type="task",
        target_id=str(task_id), detail={**data, "dueDate": due.isoformat() if due else None},
        ip=ip, trace_id=trace_id,
    )
    return _item(repo.get_task(task_id), date.today())


def list_tasks(
    repo: Repo, user: dict[str, Any], *, filters: dict[str, Any], page: int | None, page_size: int | None
) -> dict[str, Any]:
    actual_page, actual_size, offset = library.page_params(page, page_size)
    rows, total = repo.list_tasks(library.scope_for(user), filters, actual_size, offset)
    today = date.today()
    return {
        "items": [_item(row, today) for row in rows],
        "page": actual_page,
        "pageSize": actual_size,
        "total": total,
    }


def package(
    repo: Repo, user: dict[str, Any], task_id: int, *, ip: str = "", trace_id: str = ""
) -> tuple[dict[str, Any], bytes]:
    task = repo.get_task(task_id)
    if task is None:
        raise AppError("NOT_FOUND", "任务不存在")
    if not library.can_view(
        str(user.get("role") or ""), int(user.get("id") or 0), str(user.get("group_name") or ""),
        int(task["owner_id"]), str(task["owner_group"] or ""),
    ):
        raise AppError("FORBIDDEN", "无权访问该任务")
    sample_id, sample_plan = _nearest_sample(repo, task)
    data = task_package.build(task, sample_plan, sample_id)
    audit_service.record(
        repo, actor_id=int(user.get("id") or 0), action="task.package", target_type="task",
        target_id=str(task_id), detail={"sampleId": sample_id}, ip=ip, trace_id=trace_id,
    )
    return task, data


def _nearest_sample(repo: Repo, task: dict[str, Any]) -> tuple[int | None, dict[str, Any] | None]:
    sample = repo.find_sample(task["course"], int(task["week"]), int(task["session"]), task["title"])
    if sample is None:
        rows, _ = repo.list_samples({"course": task["course"], "week": task["week"]}, 1, 0)
        sample = rows[0] if rows else None
    if sample is None:
        return None, None
    raw = storage.read_sample(str(sample["json_path"]))
    if raw is None:
        return int(sample["id"]), None
    plan, problem = archive.read_json({"plan.json": raw}, "plan.json")
    return int(sample["id"]), plan if problem is None else None


def _item(task: dict[str, Any] | None, today: date) -> dict[str, Any]:
    if task is None:
        raise AppError("NOT_FOUND", "任务不存在")
    return {
        "taskId": int(task["id"]),
        "course": task["course"],
        "week": int(task["week"]),
        "session": int(task["session"]),
        "title": task["title"],
        "className": task["class_name"],
        "dueDate": task["due_date"],
        "status": task["status"],
        "ownerId": int(task["owner_id"]),
        "teacher": task.get("teacher"),
        "overdue": task_rules.is_overdue(task["due_date"], str(task["status"]), today),
        "createdAt": task["created_at"],
    }
