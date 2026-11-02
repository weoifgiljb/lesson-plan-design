# -*- coding: utf-8 -*-
"""极简内存限速器：按 key（通常是客户端 IP）做滑动窗口计数。

只覆盖单进程；多进程/多实例部署应换成 Redis 或网关限流。这里先给自助注册一个
最低限度的护栏，避免匿名批量建号（评审 F6）。
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque

_LOCK = threading.Lock()
_HITS: dict[str, Deque[float]] = {}


def allow(key: str, limit: int, window_seconds: float = 3600.0, *, now: float | None = None) -> bool:
    if limit <= 0:
        return True
    current = time.time() if now is None else now
    with _LOCK:
        hits = _HITS.setdefault(key, deque())
        while hits and current - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(current)
    return True


def reset() -> None:
    with _LOCK:
        _HITS.clear()
