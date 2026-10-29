# -*- coding: utf-8 -*-
"""任务编排：建课、列表、任务包与状态推进。"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.adapters import engine, task_package
from app.adapters.db.repo import Repo
from app.application import audit_service
from app.domain import library, task_rules
from app.domain.errors import AppError


def create(
    repo: Repo,
    user: dict[str, Any],
    payload: dict[str, Any],
    *,
    confirm: bool = False,
    ip: str = "",
    trace_id: str = "",
) -> tuple[dict[str, Any], bool]:
    data = task_rules.validate(
        payload.get("course"), payload.get("week"), payload.get("session"),
        payload.get("title"), payload.get("className", ""),
    )
    # 状态是服务端推导的，不接受客户端指定：明确拒绝，而不是静默丢弃
    requested_status = str(payload.get("status") or "draft").strip()
    if requested_status != "draft":
        raise AppError(
            "PAYLOAD_REJECTED",
            "新建任务的状态固定为 draft，后续由入库/审查/导出推进或人工回退",
            {"status": requested_status},
        )
    due = payload.get("dueDate")
    due_text = due.isoformat() if due else None
    with repo.transaction():
        existing = repo.find_task(
            data["course"], data["week"], data["session"], data["class_name"], data["title"]
        )
        if existing is not None:
            # 归属校验：别人的任务不能被 confirm 覆盖（跨教师 IDOR）
            if not _can_touch(repo, user, existing):
                audit_service.record(
                    repo, actor_id=int(user.get("id") or 0), action="authz.denied",
                    target_type="task", target_id=str(existing["id"]),
                    detail={"reason": "task_owner_mismatch", "path": "/api/v1/tasks"},
                    ip=ip, trace_id=trace_id,
                )
                raise AppError("FORBIDDEN", "该任务属于其他教师，不能覆盖")
            if not confirm:
                raise AppError(
                    "CONFLICT_STALE",
                    "同一班级的同一课题（周次/课次相同）已存在；确认覆盖请带 confirm=true",
                    {"taskId": int(existing["id"])},
                )
            # 需求 BS-10：重复建课时提示冲突，确认后才允许（这里按"更新已有任务"处理）
            repo.update_task(int(existing["id"]), title=data["title"], due_date=due_text)
            audit_service.record(
                repo, actor_id=int(user.get("id") or 0), action="task.update", target_type="task",
                target_id=str(existing["id"]), detail={**data, "dueDate": due_text, "confirmed": True},
                ip=ip, trace_id=trace_id,
            )
            return _item(repo.get_task(int(existing["id"])), date.today()), False
        task_id = repo.insert_task(
            data["course"], data["week"], data["session"], data["title"], data["class_name"],
            int(user.get("id") or 0), due_text,
        )
        audit_service.record(
            repo, actor_id=int(user.get("id") or 0), action="task.create", target_type="task",
            target_id=str(task_id), detail={**data, "dueDate": due_text},
            ip=ip, trace_id=trace_id,
        )
    return _item(repo.get_task(task_id), date.today()), True


def rollback(
    repo: Repo, user: dict[str, Any], task_id: int, *, ip: str = "", trace_id: str = ""
) -> dict[str, Any]:
    """人工回退任务状态（需求 BS-10：回退需人工并留痕）。"""
    task = repo.get_task(int(task_id))
    if task is None:
        raise AppError("NOT_FOUND", "任务不存在")
    # 归属校验：组长只能回退本组任务，不能跨组改别人状态（R2-4）
    if not _can_touch(repo, user, task):
        audit_service.record(
            repo, actor_id=int(user.get("id") or 0), action="authz.denied", target_type="task",
            target_id=str(task_id), detail={"reason": "task_scope", "path": "/api/v1/tasks/rollback"},
            ip=ip, trace_id=trace_id,
        )
        raise AppError("FORBIDDEN", "只能回退本组任务")
    current = str(task["status"])
    order = ["draft", "reviewing", "passed", "exported"]
    if current not in order or order.index(current) == 0:
        raise AppError("CONFLICT_STALE", "任务已是初始状态，无法回退")
    previous = order[order.index(current) - 1]
    with repo.transaction():
        repo.set_task_status(int(task_id), previous)
        audit_service.record(
            repo, actor_id=int(user.get("id") or 0), action="task.rollback", target_type="task",
            target_id=str(task_id), detail={"from": current, "to": previous},
            ip=ip, trace_id=trace_id,
        )
    return _item(repo.get_task(int(task_id)), date.today())


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
    template = engine.draft_plan(int(task["week"]), int(task["session"]), str(task["title"]), str(task["course"]))
    if not template:
        raise AppError("INTERNAL", "任务模板生成失败")
    sample_id = _nearest_sample(repo, task)
    data = task_package.build(task, template, sample_id)
    audit_service.record(
        repo, actor_id=int(user.get("id") or 0), action="task.package", target_type="task",
        target_id=str(task_id), detail={"sampleId": sample_id}, ip=ip, trace_id=trace_id,
    )
    return task, data


def _nearest_sample(repo: Repo, task: dict[str, Any]) -> int | None:
    sample = repo.find_sample(task["course"], int(task["week"]), int(task["session"]), task["title"])
    if sample is None:
        rows, _ = repo.list_samples(
            {"course": task["course"], "week": task["week"], "session": task["session"]}, 1, 0
        )
        sample = rows[0] if rows else None
    return int(sample["id"]) if sample is not None else None


def _can_touch(repo: Repo, user: dict[str, Any], task: dict[str, Any]) -> bool:
    """组长只能动本组任务，教师只能动自己的任务。"""
    return library.can_view(
        str(user.get("role") or ""),
        int(user.get("id") or 0),
        str(user.get("group_name") or ""),
        int(task["owner_id"]),
        str(task.get("owner_group") or ""),
    )


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
