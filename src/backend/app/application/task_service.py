# -*- coding: utf-8 -*-
"""任务编排：建课、列表、任务包与状态推进。"""
from __future__ import annotations

from datetime import date, datetime, timezone

from app.adapters import engine, task_package
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
    quadrant = task_rules.validate_quadrant(payload.get("quadrant"))
    due = payload.get("dueDate")
    owner_id = int(user.get("id") or 0)
    with repo.transaction():
        if repo.find_task(
            owner_id, data["course"], data["week"], data["session"], data["class_name"], data["title"]
        ):
            raise AppError("CONFLICT_STALE", "同一教师/课程/周次/课次/班级/课题的任务已存在")
        position = repo.next_board_position(owner_id, quadrant)
        task_id = repo.insert_task(
            data["course"], data["week"], data["session"], data["title"], data["class_name"],
            owner_id, due.isoformat() if due else None, quadrant, position,
        )
        audit_service.record(
            repo, actor_id=owner_id, action="task.create", target_type="task",
            target_id=str(task_id),
            detail={**data, "dueDate": due.isoformat() if due else None, "quadrant": quadrant},
            ip=ip, trace_id=trace_id,
        )
    return _item(repo.get_task(task_id), date.today(), user)


def list_tasks(
    repo: Repo, user: dict[str, Any], *, filters: dict[str, Any], page: int | None, page_size: int | None
) -> dict[str, Any]:
    actual_page, actual_size, offset = library.page_params(page, page_size)
    rows, total = repo.list_tasks(library.scope_for(user), filters, actual_size, offset)
    today = date.today()
    return {
        "items": [_item(row, today, user) for row in rows],
        "page": actual_page,
        "pageSize": actual_size,
        "total": total,
    }


def board(
    repo: Repo, user: dict[str, Any], *, filters: dict[str, Any]
) -> dict[str, Any]:
    rows = repo.list_board_tasks(library.scope_for(user), filters)
    today = date.today()
    items = [_item(row, today, user) for row in rows]
    counts = {quadrant: 0 for quadrant in task_rules.QUADRANTS}
    for item in items:
        counts[item["quadrant"]] = counts.get(item["quadrant"], 0) + 1
    return {
        "items": items,
        "total": len(items),
        "counts": counts,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def move(
    repo: Repo,
    user: dict[str, Any],
    task_id: int,
    payload: dict[str, Any],
    *,
    ip: str = "",
    trace_id: str = "",
) -> dict[str, Any]:
    quadrant = task_rules.validate_quadrant(payload.get("quadrant"))
    task = _owned_task(repo, user, task_id)
    if not task_rules.is_active(str(task["status"]), task["discarded_at"]):
        raise AppError("PAYLOAD_REJECTED", "已完成或已废弃任务不能移动")
    position = payload.get("position", 0)
    if isinstance(position, bool) or not isinstance(position, int) or position < 0:
        raise AppError("PAYLOAD_REJECTED", "position 必须是非负整数")
    version = payload.get("boardVersion", task["board_version"])
    if isinstance(version, bool) or not isinstance(version, int):
        raise AppError("PAYLOAD_REJECTED", "boardVersion 必须是整数")
    owner_id = int(task["owner_id"])
    with repo.transaction():
        current = repo.get_task(task_id)
        if current is None:
            raise AppError("NOT_FOUND", "任务不存在")
        if int(current["board_version"]) != version:
            raise AppError(
                "CONFLICT_STALE",
                "任务看板已被修改，请刷新后重试",
                {"boardVersion": int(current["board_version"])},
            )
        target_position = _apply_move(
            repo,
            task_id,
            owner_id,
            str(current["quadrant"]),
            quadrant,
            position,
            version,
        )
        audit_service.record(
            repo,
            actor_id=int(user.get("id") or 0),
            action="task.board.move",
            target_type="task",
            target_id=str(task_id),
            detail={"from": current["quadrant"], "to": quadrant, "position": target_position},
            ip=ip,
            trace_id=trace_id,
        )
    return _item(repo.get_task(task_id), date.today(), user)


def _apply_move(
    repo: Repo,
    task_id: int,
    owner_id: int,
    from_quadrant: str,
    to_quadrant: str,
    position: int,
    version: int,
) -> int:
    source_ids = repo.task_ids_in_quadrant(owner_id, from_quadrant)
    source_ids = [item for item in source_ids if item != task_id]
    if from_quadrant == to_quadrant:
        target_ids = source_ids
        target_ids.insert(min(position, len(target_ids)), task_id)
        repo.update_task_positions(target_ids)
    else:
        target_ids = repo.task_ids_in_quadrant(owner_id, to_quadrant)
        target_ids.insert(min(position, len(target_ids)), task_id)
        repo.update_task_positions(source_ids)
        repo.update_task_positions(target_ids)
    target_position = target_ids.index(task_id)
    if not repo.update_task_board(task_id, to_quadrant, target_position, version):
        raise AppError("CONFLICT_STALE", "任务看板已被修改，请刷新后重试")
    return target_position


def discard(
    repo: Repo, user: dict[str, Any], task_id: int, *, ip: str = "", trace_id: str = ""
) -> dict[str, Any]:
    task = _owned_task(repo, user, task_id)
    if task["discarded_at"] is not None:
        return _item(task, date.today(), user)
    if not task_rules.is_active(str(task["status"]), None):
        raise AppError("PAYLOAD_REJECTED", "已完成任务不能废弃")
    with repo.transaction():
        repo.set_task_discarded(task_id, datetime.now(timezone.utc).isoformat())
        audit_service.record(
            repo,
            actor_id=int(user.get("id") or 0),
            action="task.discard",
            target_type="task",
            target_id=str(task_id),
            detail={"status": task["status"]},
            ip=ip,
            trace_id=trace_id,
        )
    return _item(repo.get_task(task_id), date.today(), user)


def restore(
    repo: Repo, user: dict[str, Any], task_id: int, *, ip: str = "", trace_id: str = ""
) -> dict[str, Any]:
    task = _owned_task(repo, user, task_id)
    if task["discarded_at"] is None:
        return _item(task, date.today(), user)
    with repo.transaction():
        repo.set_task_discarded(task_id, None)
        audit_service.record(
            repo,
            actor_id=int(user.get("id") or 0),
            action="task.restore",
            target_type="task",
            target_id=str(task_id),
            detail={},
            ip=ip,
            trace_id=trace_id,
        )
    return _item(repo.get_task(task_id), date.today(), user)


def _owned_task(repo: Repo, user: dict[str, Any], task_id: int) -> dict[str, Any]:
    task = repo.get_task(task_id)
    if task is None:
        raise AppError("NOT_FOUND", "任务不存在")
    if int(task["owner_id"]) != int(user.get("id") or 0):
        raise AppError("FORBIDDEN", "只能操作本人任务")
    return task


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


def _item(task: dict[str, Any] | None, today: date, viewer: dict[str, Any]) -> dict[str, Any]:
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
        "quadrant": task["quadrant"],
        "boardPosition": int(task["board_position"]),
        "boardVersion": int(task["board_version"]),
        "discarded": task["discarded_at"] is not None,
        "discardedAt": task["discarded_at"],
        "canEdit": int(task["owner_id"]) == int(viewer.get("id") or 0),
        "overdue": task_rules.is_overdue(task["due_date"], str(task["status"]), today),
        "createdAt": task["created_at"],
    }
