# -*- coding: utf-8 -*-
"""BS-13 站内通知：审查修复、任务逾期、导出完成、报告过期。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.adapters.db.repo import Repo

KIND_TITLES = {
    "review_repair": "审查需修复",
    "task_overdue": "任务逾期",
    "export_done": "导出完成",
    "report_expired": "报告已过期",
}


def notify(
    repo: Repo,
    user_id: int,
    kind: str,
    body: str,
    *,
    target_type: str = "",
    target_id: str = "",
) -> int:
    title = KIND_TITLES.get(kind, kind)
    return repo.insert_notification_once(user_id, kind, title, body, target_type, target_id)


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "kind": row["kind"],
        "title": row["title"],
        "body": row.get("body") or "",
        "targetType": row.get("target_type") or "",
        "targetId": row.get("target_id") or "",
        "createdAt": row.get("created_at"),
        "readAt": row.get("read_at"),
        "read": row.get("read_at") is not None,
    }


def notify_import(
    repo: Repo, owner_id: int, plan: dict[str, Any], plan_id: int, version_no: int, passed: bool
) -> None:
    title = plan.get("contentTitle") or plan_id
    if not passed:
        notify(
            repo, owner_id, "review_repair",
            f"教案《{title}》审查未通过，请修复后重新审校。",
            target_type="plan", target_id=str(plan_id),
        )
    if version_no > 1:
        notify(
            repo, owner_id, "report_expired",
            f"教案《{title}》已产生新版本，旧审查报告不再适用。",
            target_type="plan", target_id=str(plan_id),
        )


def notify_overdue(repo: Repo, user: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for task in repo.list_overdue_tasks(int(user["id"]), now):
        notify(
            repo,
            int(user["id"]),
            "task_overdue",
            f"任务《{task['title']}》已到截止时间 {task['due_date']}，请处理。",
            target_type="task",
            target_id=str(task["id"]),
        )


def list_notifications(
    repo: Repo, user: dict[str, Any], *, unread_only: bool, limit: int, offset: int
) -> dict[str, Any]:
    notify_overdue(repo, user)
    rows, total, unread = repo.list_notifications(int(user["id"]), unread_only, limit, offset)
    return {"items": [_payload(row) for row in rows], "total": total, "unread": unread}


def mark_read(repo: Repo, user: dict[str, Any], notification_id: int) -> dict[str, Any]:
    changed = repo.mark_notification_read(int(user["id"]), notification_id)
    return {"id": notification_id, "read": True, "changed": changed}


def mark_all_read(repo: Repo, user: dict[str, Any]) -> dict[str, Any]:
    return {"read": True, "changed": repo.mark_all_notifications_read(int(user["id"]))}
