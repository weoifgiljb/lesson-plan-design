# -*- coding: utf-8 -*-
"""建课冲突编排：同身份任务已存在时的 409 语义、覆盖确认与留痕（BS-10/T1/T2）。"""
from __future__ import annotations

from typing import Any

from app.adapters.db.repo import Repo
from app.application import audit_service
from app.domain import task_rules
from app.domain.errors import AppError


def guard(
    repo: Repo,
    user: dict[str, Any],
    task: dict[str, Any],
    confirm: bool,
    *,
    ip: str = "",
    trace_id: str = "",
) -> None:
    """未确认 → 409 冲突；确认但无权覆盖 → 403 越权（真实越权留痕，不放水）。"""
    if not confirm:
        raise_conflict(repo, user, task)
    if not task_rules.can_overwrite(user, task):
        deny(repo, user, task, ip=ip, trace_id=trace_id)


def raise_conflict(repo: Repo, user: dict[str, Any], task: dict[str, Any]) -> None:
    """409 冲突：不写 authz.denied（T2）；占用者信息是否回传由 domain 决定。"""
    owner_name = ""
    if task_rules.can_touch(user, task):
        owner_name = str((repo.get_task(int(task["id"])) or {}).get("teacher") or "")
    raise AppError(*task_rules.conflict_for(user, task, owner_name))


def deny(
    repo: Repo, user: dict[str, Any], task: dict[str, Any], *, ip: str = "", trace_id: str = ""
) -> None:
    """显式覆盖他人任务：事务外写审计；事务内由 create 的回滚钩子补写（R3-F2）。

    响应体不回传 taskId：可触及（同组）也不需要，跨组更不能泄露（T1/T2）。
    """
    audit_service.record(
        repo, actor_id=int(user.get("id") or 0), action="authz.denied",
        target_type="task", target_id=str(task["id"]),
        detail={"reason": "task_owner_mismatch", "path": "/api/v1/tasks"},
        ip=ip, trace_id=trace_id,
    )
    raise AppError("FORBIDDEN", task_rules.FORBIDDEN_OVERWRITE)


def apply_confirmed(
    repo: Repo,
    user: dict[str, Any],
    task: dict[str, Any],
    data: dict[str, Any],
    due_text: str | None,
    *,
    ip: str = "",
    trace_id: str = "",
) -> None:
    """确认覆盖：已废弃任务先恢复再更新，两步都留痕，避免"建课成功但任务仍废弃"。

    只更新截止日期（既有 BS-10 行为）；象限变更走 PATCH /tasks/{id}/board，不在这里顺带改。
    """
    task_id = int(task["id"])
    if task.get("discarded_at") is not None:
        repo.set_task_discarded(task_id, None)
        audit_service.record(
            repo, actor_id=int(user.get("id") or 0), action="task.restore", target_type="task",
            target_id=str(task_id), detail={"reason": "recreate_after_discard"},
            ip=ip, trace_id=trace_id,
        )
    repo.update_task(task_id, title=data["title"], due_date=due_text)
    audit_service.record(
        repo, actor_id=int(user.get("id") or 0), action="task.update", target_type="task",
        target_id=str(task_id), detail={**data, "dueDate": due_text, "confirmed": True},
        ip=ip, trace_id=trace_id,
    )
