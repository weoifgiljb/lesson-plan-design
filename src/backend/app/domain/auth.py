# -*- coding: utf-8 -*-
"""登录与会话规则：锁定、过期、CSRF 判定，全部可单测。"""
from __future__ import annotations

import hmac

SESSION_TTL_HOURS = 8
MIN_OVERRIDE_REASON = 6


def next_failure(failed_count: int, max_failures: int) -> tuple[int, bool]:
    """返回 (新的失败次数, 是否应锁定)。"""
    count = int(failed_count) + 1
    return count, count >= max_failures


def should_lock(failed_count: int, max_failures: int) -> bool:
    return int(failed_count) >= max_failures


def csrf_matches(expected: str, provided: str) -> bool:
    if not isinstance(expected, str) or not isinstance(provided, str):
        return False
    if not expected or not provided:
        return False
    return hmac.compare_digest(expected, provided)


def reason_is_shorter(reason: str, minimum: int = MIN_OVERRIDE_REASON) -> bool:
    return not isinstance(reason, str) or len(reason.strip()) < minimum
