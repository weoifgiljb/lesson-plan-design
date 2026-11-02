# -*- coding: utf-8 -*-
"""日期筛选边界：把「本地日」换成 UTC 时间戳区间，纯函数。

部署地在国内（Asia/Shanghai，无夏令时），因此固定 +08:00 偏移，不依赖 tzdata。
`dateFrom/dateTo` 语义是本地日：本地 2026-10-27 00:00 起、到 2026-10-28 00:00 前。
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

LOCAL_TZ = timezone(timedelta(hours=8))


def start_of(day: date) -> str:
    local = datetime.combine(day, time.min, tzinfo=LOCAL_TZ)
    return local.astimezone(timezone.utc).isoformat()


def end_exclusive(day: date) -> str:
    """dateTo 取「本地次日零点」开区间，避免当天 23:59:59 被漏掉。"""
    if day >= date.max:
        return datetime.max.replace(tzinfo=timezone.utc).isoformat()
    local = datetime.combine(day + timedelta(days=1), time.min, tzinfo=LOCAL_TZ)
    return local.astimezone(timezone.utc).isoformat()
