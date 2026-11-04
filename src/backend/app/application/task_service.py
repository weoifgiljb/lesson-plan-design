# -*- coding: utf-8 -*-
"""任务编排：建课、列表、任务包与状态推进。"""
from __future__ import annotations

from datetime import date, datetime, timezone
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
    quadrant = task_rules.validate_quadrant(payload.get("quadrant"))
    due = payload.get("dueDate")
    due_text = due.isoformat() if due else None
    # 归属校验放在事务外：越权审计必须真正落库（事务内 raise 会把审计一起回滚，R3-F2）
    probe = repo.find_task(
        data["course"], data["week"], data["session"], data["class_name"], data["title"]
    )
    if probe is not None and not _can_touch(repo, user, probe):
        audit_service.record(
            repo, actor_id=int(user.get("id") or 0), action="authz.denied",
            target_type="task", target_id=str(probe["id"]),
            detail={"reason": "task_owner_mismatch", "path": "/api/v1/tasks"},
            ip=ip, trace_id=trace_id,
        )
        raise AppError("FORBIDDEN", "该任务属于其他教师，不能覆盖")
    with repo.transaction():
        existing = repo.find_task(
            data["course"], data["week"], data["session"], data["class_name"], data["title"]
        )
        if existing is not None:
            if not _can_touch(repo, user, existing):
                raise AppError("FORBIDDEN", "该任务属于其他教师，不能覆盖")
            if not confirm:
                raise AppError(
                    "CONFLICT_STALE",
                    "同一班级的同一课题（周次/课次相同）已存在；确认覆盖请带 confirm=true",
                    {"taskId": int(existing["id"])},
                )
            if int(existing["owner_id"]) != int(user.get("id") or 0) and str(user.get("role")) != "admin":
                # 组内共享只读+推进；覆盖（改标题/截止）限定本人或管理员（R3-F6）
                raise AppError("FORBIDDEN", "只能覆盖自己创建的任务；他人任务请由本人或管理员处理")
            # 需求 BS-10：重复建课时提示冲突，确认后才允许（这里按"更新已有任务"处理）
            repo.update_task(int(existing["id"]), title=data["title"], due_date=due_text)
            audit_service.record(
                repo, actor_id=int(user.get("id") or 0), action="task.update", target_type="task",
                target_id=str(existing["id"]), detail={**data, "dueDate": due_text, "confirmed": True},
                ip=ip, trace_id=trace_id,
            )
            return _item(repo.get_task(int(existing["id"])), date.today()), False
        owner_id = int(user.get("id") or 0)
        task_id = repo.insert_task(
            data["course"], data["week"], data["session"], data["title"], data["class_name"],
            owner_id, due_text, str(user.get("group_name") or ""),
            quadrant, repo.next_board_position(owner_id, quadrant),
        )
        audit_service.record(
            repo, actor_id=int(user.get("id") or 0), action="task.create", target_type="task",
            target_id=str(task_id), detail={**data, "dueDate": due_text},
            ip=ip, trace_id=trace_id,
        )
    return _item(repo.get_task(task_id), date.today(), user), True


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
    rows, total = repo.list_tasks(library.task_scope_for(user), filters, actual_size, offset)
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
    if not task_rules.is_active(str(task["status"]), task.get("discarded_at")):
        raise AppError("PAYLOAD_REJECTED", "已完成或已废弃任务不能移动")
    position = payload.get("position", 0)
    if isinstance(position, bool) or not isinstance(position, int) or position < 0:
        raise AppError("PAYLOAD_REJECTED", "position 必须是非负整数")
    version = payload.get("boardVersion", int(task.get("board_version") or 0))
    if isinstance(version, bool) or not isinstance(version, int):
        raise AppError("PAYLOAD_REJECTED", "boardVersion 必须是整数")
    owner_id = int(task["owner_id"])
    with repo.transaction():
        current = repo.get_task(task_id)
        if current is None:
            raise AppError("NOT_FOUND", "任务不存在")
        if int(current.get("board_version") or 0) != version:
            raise AppError(
                "CONFLICT_STALE",
                "任务看板已被修改，请刷新后重试",
                {"boardVersion": int(current.get("board_version") or 0)},
            )
        target_position = _apply_move(
            repo, task_id, owner_id, str(current.get("quadrant") or task_rules.DEFAULT_QUADRANT),
            quadrant, position, version,
        )
        audit_service.record(
            repo,
            actor_id=int(user.get("id") or 0),
            action="task.board.move",
            target_type="task",
            target_id=str(task_id),
            detail={"from": current.get("quadrant"), "to": quadrant, "position": target_position},
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
    source_ids = [item for item in repo.task_ids_in_quadrant(owner_id, from_quadrant) if item != task_id]
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
    if task.get("discarded_at") is not None:
        return _item(task, date.today())
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
    if task.get("discarded_at") is None:
        return _item(task, date.today())
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
    task = repo.get_task(int(task_id))
    if task is None:
        raise AppError("NOT_FOUND", "任务不存在")
    if not _can_touch(repo, user, task):
        raise AppError("FORBIDDEN", "只能操作本人或本组任务")
    return task


def package(
    repo: Repo, user: dict[str, Any], task_id: int, *, ip: str = "", trace_id: str = ""
) -> tuple[dict[str, Any], bytes]:
    task = repo.get_task(task_id)
    if task is None:
        raise AppError("NOT_FOUND", "任务不存在")
    if not _can_touch(repo, user, task):
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
    """本人的任务、或本组任务（组长建的任务组内教师可推进）；管理员全部。"""
    if str(user.get("role") or "") == "admin":
        return True
    if int(user.get("id") or 0) == int(task["owner_id"]):
        return True
    group = str(user.get("group_name") or "").strip()
    task_group = str(task.get("group_name") or task.get("owner_group") or "").strip()
    return bool(group) and group == task_group


def _item(
    task: dict[str, Any] | None, today: date, user: dict[str, Any] | None = None
) -> dict[str, Any]:
    if task is None:
        raise AppError("NOT_FOUND", "任务不存在")
    owner_id = int(task["owner_id"])
    same_owner = user is None or int(user.get("id") or 0) == owner_id
    can_edit = same_owner or str((user or {}).get("role") or "") == "admin"
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
        "quadrant": task.get("quadrant") or task_rules.DEFAULT_QUADRANT,
        "boardPosition": int(task.get("board_position") or 0),
        "boardVersion": int(task.get("board_version") or 0),
        "discardedAt": task.get("discarded_at"),
        "discarded": task.get("discarded_at") is not None,
        "canEdit": can_edit,
    }
