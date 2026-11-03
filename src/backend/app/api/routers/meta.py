# -*- coding: utf-8 -*-
"""平台元数据：把后端权威枚举/限制一次性下发给前端。

前端不应自己维护状态、角色等封闭集合——`app/domain` 里已有唯一来源，
这里把它们序列化成只读响应，避免前端再抄一份（见「前端硬编码审计」）。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import current_context
from app.api.responses import error_responses
from app.config import (
    MAX_PACKAGE_BYTES,
    MAX_PACKAGE_FILES,
    MAX_SAMPLE_BYTES,
    MIN_PASSWORD_LENGTH,
)
from app.domain import library, report_rules, roles, task_rules, user_rules

router = APIRouter()

#: 展示顺序即业务推进顺序
TASK_STATUS_ORDER = ("draft", "reviewing", "passed", "exported")
TASK_STATUS_LABELS = {
    "draft": "待开始",
    "reviewing": "审查中",
    "passed": "已通过",
    "exported": "已导出",
}
REVIEW_STATUS_LABELS = {
    "structure_invalid": "结构失败",
    "pending_reviewer": "待审",
    "needs_repair": "待修复",
    "passed": "通过",
    "passed_with_override": "放行通过",
    "passed_with_accepted_minor": "接受轻微",
}
REPORT_STATUS_ORDER = (
    "structure_invalid",
    "pending_reviewer",
    "needs_repair",
    "passed",
    "passed_with_override",
    "passed_with_accepted_minor",
)
QUADRANT_LABELS = {
    "urgent_important": "紧急且重要",
    "important_not_urgent": "重要不紧急",
    "urgent_not_important": "紧急不重要",
    "not_urgent_not_important": "不紧急不重要",
}


@router.get(
    "/meta",
    responses=error_responses("AUTH_REQUIRED:未登录"),
    summary="平台元数据（枚举/角色/限制）",
)
def meta(context: dict[str, Any] = Depends(current_context)) -> dict[str, Any]:
    return {
        "roles": [{"code": code, "label": roles.ROLE_LABELS[code]} for code in roles.ROLES],
        "taskStatuses": [
            {"code": code, "label": TASK_STATUS_LABELS[code], "rank": task_rules.TASK_RANK[code]}
            for code in TASK_STATUS_ORDER
        ],
        "quadrants": [
            {"code": code, "label": QUADRANT_LABELS[code]}
            for code in sorted(task_rules.QUADRANTS)
        ],
        "defaultQuadrant": task_rules.DEFAULT_QUADRANT,
        "reviewStatuses": [
            {"code": code, "label": REVIEW_STATUS_LABELS[code]}
            for code in REPORT_STATUS_ORDER
            if code in report_rules.ALLOWED_STATUS
        ],
        "limits": {
            "passwordMinLength": MIN_PASSWORD_LENGTH,
            # 用户名/显示名长度：注册页（匿名）用本地常量兜底，管理端可直接吃这里
            "usernameMinLength": user_rules.USERNAME_MIN,
            "usernameMaxLength": user_rules.USERNAME_MAX,
            "displayNameMaxLength": user_rules.DISPLAY_NAME_MAX,
            "pageSizeDefault": library.PAGE_SIZE_DEFAULT,
            "pageSizeMax": library.PAGE_SIZE_MAX,
            "packageMaxBytes": MAX_PACKAGE_BYTES,
            "packageMaxFiles": MAX_PACKAGE_FILES,
            "sampleMaxBytes": MAX_SAMPLE_BYTES,
        },
    }
