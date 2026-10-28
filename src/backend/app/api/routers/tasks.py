# -*- coding: utf-8 -*-
"""任务：建课、列表与任务包下载。"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel

from app.api.deps import require_csrf_role, require_role
from app.application import task_service

router = APIRouter()


class TaskCreate(BaseModel):
    course: str
    week: int
    session: int
    title: str
    className: str = ""
    dueDate: date | None = None


@router.get("/tasks")
def list_tasks(
    context: dict[str, Any] = Depends(require_role("teacher", "lead")),
    course: str | None = None,
    week: int | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = Query(20, alias="pageSize"),
) -> dict[str, Any]:
    return task_service.list_tasks(
        context["repo"], context["user"],
        filters={"course": course, "week": week, "status": status},
        page=page, page_size=page_size,
    )


@router.post("/tasks", status_code=201)
def create_task(
    request: Request,
    payload: TaskCreate,
    context: dict[str, Any] = Depends(require_csrf_role("teacher", "lead")),
) -> dict[str, Any]:
    return task_service.create(
        context["repo"], context["user"], payload.model_dump(),
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
