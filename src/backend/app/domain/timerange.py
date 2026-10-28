# -*- coding: utf-8 -*-
"""日期筛选边界：按 UTC 天区间转换，纯函数。"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone


def start_of(day: date) -> str:
    return datetime.combine(day, time.min, tzinfo=timezone.utc).isoformat()


def end_exclusive(day: date) -> str:
    """dateTo 取"次日零点开区间"，避免当天 23:59:59 被漏掉。"""
    return datetime.combine(day + timedelta(days=1), time.min, tzinfo=timezone.utc).isoformat()
