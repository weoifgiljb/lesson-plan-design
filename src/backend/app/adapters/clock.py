# -*- coding: utf-8 -*-
"""时间适配：统一 UTC ISO 8601，测试可替换。

同格式（+00:00 时区）的 ISO 字符串按字典序比较与按时间比较等价，
因此本模块不解析、不抛异常，避免在 adapter 里重复错误边界。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now().isoformat()


def iso_after(hours: float) -> str:
    return (now() + timedelta(hours=hours)).isoformat()


def is_past(value: str) -> bool:
    return not isinstance(value, str) or value <= now_iso()
