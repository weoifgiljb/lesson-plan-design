# -*- coding: utf-8 -*-
"""任务：建课、列表与任务包下载。"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel

from app.api.deps import require_csrf_role, require_role
from app.api.responses import error_responses
from app.application import task_service

router = APIRouter()


class TaskCreate(BaseModel):
    course: str
    week: int
    session: int
    title: str
    className: str = ""
    dueDate: date | None = None
    # 状态由服务端控制：新建固定 draft，后续由入库/审查/导出推进，或走人工回退接口。
    # 收下这个字段只为给出明确报错，避免前端传了被静默忽略。
    status: str | None = None
    quadrant: str | None = None


class TaskMove(BaseModel):
    quadrant: str
    position: int
    boardVersion: int


@router.get("/tasks")
def list_tasks(
    context: dict[str, Any] = Depends(require_role("teacher", "lead")),
    course: str | None = None,
    week: int | None = None,
    status: str | None = None,
    quadrant: str | None = None,
    teacher: str | None = None,
    discarded: bool | None = None,
    page: int = 1,
    page_size: int = Query(20, alias="pageSize"),
) -> dict[str, Any]:
    return task_service.list_tasks(
        context["repo"], context["user"],
        filters={
            "course": course,
            "week": week,
            "status": status,
            "quadrant": quadrant,
            "teacher": teacher,
            "discarded": discarded,
        },
        page=page, page_size=page_size,
    )


@router.get("/tasks/board")
def task_board(
    context: dict[str, Any] = Depends(require_role("teacher", "lead")),
    course: str | None = None,
    week: int | None = None,
    teacher: str | None = None,
) -> dict[str, Any]:
    return task_service.board(
        context["repo"], context["user"],
        filters={"course": course, "week": week, "teacher": teacher},
    )


@router.post(
    "/tasks",
    status_code=201,
    responses={200: {"description": "confirm=true 且已存在同一任务时，更新并返回已有任务"}},
)
def create_task(
    request: Request,
    response: Response,
    payload: TaskCreate,
    confirm: bool = False,
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead")),
) -> dict[str, Any]:
    result, created = task_service.create(
        context["repo"], context["user"], payload.model_dump(),
        confirm=confirm, ip=_client_ip(request), trace_id=_trace_id(request),
    )
    if not created:
        response.status_code = 200
    return result


@router.post("/tasks/{task_id}/rollback")
def rollback_task(
    request: Request,
    task_id: int,
    context: dict[str, Any] = Depends(require_csrf_role("admin", "lead")),
) -> dict[str, Any]:
    return task_service.rollback(
        context["repo"], context["user"], task_id,
        ip=_client_ip(request), trace_id=_trace_id(request),
    )


@router.patch(
    "/tasks/{task_id}/board",
    responses=error_responses("AUTH_REQUIRED:未登录", "FORBIDDEN:只能操作本人或本组任务",
                              "NOT_FOUND:任务不存在", "CONFLICT_STALE:看板已被修改",
                              "PAYLOAD_REJECTED:参数不合法"),
)
def move_task(
    request: Request,
    task_id: int,
    payload: TaskMove,
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead")),
) -> dict[str, Any]:
    return task_service.move(
        context["repo"], context["user"], task_id, payload.model_dump(),
        ip=_client_ip(request), trace_id=_trace_id(request),
    )


@router.post("/tasks/{task_id}/discard", responses=error_responses(
    "AUTH_REQUIRED:未登录", "FORBIDDEN:只能操作本人或本组任务",
    "NOT_FOUND:任务不存在", "PAYLOAD_REJECTED:已完成任务不能废弃"))
def discard_task(
    request: Request,
    task_id: int,
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead")),
) -> dict[str, Any]:
    return task_service.discard(
        context["repo"], context["user"], task_id,
        ip=_client_ip(request), trace_id=_trace_id(request),
    )


@router.post("/tasks/{task_id}/restore", responses=error_responses(
    "AUTH_REQUIRED:未登录", "FORBIDDEN:只能操作本人或本组任务", "NOT_FOUND:任务不存在"))
def restore_task(
    request: Request,
    task_id: int,
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead")),
) -> dict[str, Any]:
    return task_service.restore(
        context["repo"], context["user"], task_id,
        ip=_client_ip(request), trace_id=_trace_id(request),
    )


@router.get("/tasks/{task_id}/package")
def task_package(
    request: Request,
    task_id: int,
    context: dict[str, Any] = Depends(require_role("teacher", "lead")),
) -> Response:
    task, data = task_service.package(
        context["repo"], context["user"], task_id,
        ip=_client_ip(request), trace_id=_trace_id(request),
    )
    filename = f"task-{task['id']}-{task['week']}-{task['session']}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _client_ip(request: Request) -> str:
    return str(request.client.host) if request.client else ""


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", ""))
