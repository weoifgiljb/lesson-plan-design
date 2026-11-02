# -*- coding: utf-8 -*-
"""当前用户信息。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api import schemas
from app.api.deps import current_context

router = APIRouter()


@router.get("/me", responses={401: {"description": "未登录或会话已失效"}})
def me(context: dict[str, Any] = Depends(current_context)) -> dict[str, Any]:
    return {
        "user": schemas.user_payload(context["user"]),
        "csrfToken": str(context["session"].get("csrf_token") or ""),
    }
