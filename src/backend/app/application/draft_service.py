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
    task = _touchable_task(repo, user, task_id)
    plan = engine.draft_plan(
        int(task["week"]), int(task["session"]), str(task["title"]), str(task["course"])
    )
    if not plan:
        raise AppError("INTERNAL", "任务模板生成失败")
    plan_hash = engine.plan_hash(plan)
    owner_id = int(user.get("id") or 0)
    task_id = int(task["id"])
    with repo.transaction():
        # 事务内复检：模板生成与写库之间任务可能被废弃或改名，不能把旧标题的草稿绑上去
        _recheck(repo, task)
        plan_id = repo.find_or_create_plan(owner_id, plan)
        bound = repo.task_for_plan(plan_id)
        if bound is not None and int(bound["id"]) != task_id:
            # 教案身份不含班级（唯一索引是 owner+课程+周次+课次+课题），绑定别的任务时必须显式拒绝
            raise AppError(
                "PAYLOAD_REJECTED",
                "该课题已有教案，但绑定的是其他班级的任务；请换课题或先在教案库删除旧教案",
                {"planId": plan_id, "boundTaskId": int(bound["id"])},
            )
        existing = repo.list_versions(plan_id)
        if existing:
            if bound is None:
                # 之前入库时启发式匹配落空导致未绑定：重试补绑，避免任务永远看不到草稿
                _bind_task(repo, plan, plan_id, task_id)
            return _duplicate(repo, plan_id, existing[-1], task_id, owner_id, ip, trace_id)
        version_no = _write_draft(repo, plan_id, plan, plan_hash)
        _bind_task(repo, plan, plan_id, task_id)
        audit_service.record(
            repo,
            actor_id=owner_id,
            action="task.draft",
            target_type="task",
            target_id=str(task_id),
            detail={"planId": plan_id, "versionNo": version_no, "planHash": plan_hash},
            ip=ip,
            trace_id=trace_id,
            after_hash=plan_hash,
        )
    return _payload(plan_id, version_no, {"plan_hash": plan_hash, "status": ""}, duplicate=False)


def _touchable_task(repo: Repo, user: dict[str, Any], task_id: int) -> dict[str, Any]:
    """草稿是新内容，只有任务本人（或管理员）能建：组内共享是只读+推进，不替别人建教案。"""
    task = repo.get_task(int(task_id))
    if task is None:
        raise AppError("NOT_FOUND", "任务不存在")
    if not task_rules.can_overwrite(user, task):
        raise AppError("FORBIDDEN", "只能为自己创建的任务生成草稿")
    if task.get("discarded_at") is not None:
        raise AppError("PAYLOAD_REJECTED", "已废弃任务不能生成草稿")
    return task


def _recheck(repo: Repo, task: dict[str, Any]) -> None:
    fresh = repo.get_task(int(task["id"]))
    if fresh is None or fresh.get("discarded_at") is not None:
        raise AppError("PAYLOAD_REJECTED", "已废弃任务不能生成草稿")
    if (fresh["title"], fresh["week"], fresh["session"], fresh["course"]) != (
        task["title"], task["week"], task["session"], task["course"]
    ):
        raise AppError("CONFLICT_STALE", "任务已被修改，请刷新后重试")


def _write_draft(repo: Repo, plan_id: int, plan: dict[str, Any], plan_hash: str) -> int:
    """落 v1 草稿版本并切成当前版本；返回版本号。"""
    info = engine.engine_versions()
    version_no = repo.next_version_no(plan_id)
    version_id, created = repo.insert_version_or_existing(
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
    if not created:
        # 唯一键冲突时返回的是既有版本：不能把旧版本推成当前版本，也不能声称新建
        raise AppError("CONFLICT_STALE", "草稿版本冲突，请重试")
    repo.set_current_version(plan_id, version_id)
    repo.insert_sync_event("version", plan_id, version_id)
    return version_no


def _bind_task(repo: Repo, plan: dict[str, Any], plan_id: int, task_id: int) -> None:
    """只挂任务不推进状态（任务仍 draft）；绑定失败说明任务非本人创建，直接拒绝。"""
    repo.attach_task_for_plan(plan_id, plan, "draft", task_id=task_id)
    linked = repo.task_for_plan(plan_id)
    if linked is None or int(linked["id"]) != task_id:
        raise AppError("FORBIDDEN", "只能为自己创建的任务生成草稿")


def _payload(
    plan_id: int, version_no: int, version: dict[str, Any], *, duplicate: bool
) -> dict[str, Any]:
    return {
        "planId": plan_id,
        "versionNo": version_no,
        "planHash": str(version.get("plan_hash") or ""),
        "reviewStatus": str(version.get("status") or ""),
        "duplicate": duplicate,
    }


def _duplicate(
    repo: Repo, plan_id: int, current: dict[str, Any], task_id: int,
    actor_id: int, ip: str, trace_id: str,
) -> dict[str, Any]:
    """重复点击也要留痕（与导入的 plan.import.duplicate 对齐，BS-06 写操作留痕）。"""
    version_no = int(current["version_no"])
    audit_service.record(
        repo,
        actor_id=actor_id,
        action="task.draft.duplicate",
        target_type="task",
        target_id=str(task_id),
        detail={"planId": plan_id, "versionNo": version_no},
        ip=ip,
        trace_id=trace_id,
    )
    return _payload(plan_id, version_no, current, duplicate=True)
