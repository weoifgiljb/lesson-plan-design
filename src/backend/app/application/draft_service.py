# -*- coding: utf-8 -*-
"""平台内草稿教案：把任务落成校标骨架 v1（PreMortem T3 的无 Agent 降级路径）。

只复用插件草稿器 `engine.draft_plan()`，不伪造审查报告：草稿版本 `report_sha256=''`
（"未审查"哨兵），因此导出门禁天然拒绝，等教师用契约包覆盖出新版本。
"""
from __future__ import annotations

import json
from typing import Any

from app.adapters import engine
from app.adapters.db.repo import Repo
from app.application import audit_service
from app.domain import task_rules, versions
from app.domain.errors import AppError


def draft_from_task(
    repo: Repo, user: dict[str, Any], task_id: int, *, ip: str = "", trace_id: str = ""
) -> dict[str, Any]:
    """生成或返回该任务的草稿教案；同一身份已有版本时幂等返回，不覆盖已审查版本。"""
    task = repo.get_task(int(task_id))
    if task is None:
        raise AppError("NOT_FOUND", "任务不存在")
    if not task_rules.can_touch(user, task):
        raise AppError("FORBIDDEN", "只能操作本人或本组任务")
    if task.get("discarded_at") is not None:
        raise AppError("PAYLOAD_REJECTED", "已废弃任务不能生成草稿")
    plan = engine.draft_plan(
        int(task["week"]), int(task["session"]), str(task["title"]), str(task["course"])
    )
    if not plan:
        raise AppError("INTERNAL", "任务模板生成失败")
    plan_hash = engine.plan_hash(plan)
    owner_id = int(user.get("id") or 0)
    with repo.transaction():
        plan_id = repo.find_or_create_plan(owner_id, plan)
        existing = repo.list_versions(plan_id)
        if existing:
            current = existing[-1]
            return {
                "planId": plan_id,
                "versionNo": int(current["version_no"]),
                "planHash": str(current.get("plan_hash") or ""),
                "reviewStatus": str(current.get("status") or ""),
                "duplicate": True,
            }
        info = engine.engine_versions()
        version_no = repo.next_version_no(plan_id)
        version_id, _created = repo.insert_version_or_existing(
            plan_id,
            version_no,
            json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            plan_hash,
            "",
            int(versions.VERSIONS["schemaVersion"]),
            str(versions.VERSIONS["rubricVersion"]),
            str(info.get("engineVersion") or ""),
            str(info.get("templateVersion") or ""),
            source="draft",
        )
        repo.set_current_version(plan_id, version_id)
        repo.insert_sync_event("version", plan_id, version_id)
        # 只挂任务不推进状态：任务仍为 draft，等契约包入库/审查/导出才推进（BS-10 状态机）
        repo.attach_task_for_plan(plan_id, plan, "draft", task_id=int(task["id"]))
        audit_service.record(
            repo,
            actor_id=owner_id,
            action="task.draft",
            target_type="task",
            target_id=str(int(task["id"])),
            detail={"planId": plan_id, "versionNo": int(version_no), "planHash": plan_hash},
            ip=ip,
            trace_id=trace_id,
            after_hash=plan_hash,
        )
    return {
        "planId": plan_id,
        "versionNo": int(version_no),
        "planHash": plan_hash,
        "reviewStatus": "",
        "duplicate": False,
    }
