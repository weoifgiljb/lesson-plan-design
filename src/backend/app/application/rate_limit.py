# -*- coding: utf-8 -*-
"""极简内存限速器：按 key（通常是客户端 IP）做滑动窗口计数。

只覆盖单进程；多进程/多实例部署应换成 Redis 或网关限流。这里先给自助注册一个
最低限度的护栏，避免匿名批量建号（评审 F6）。

表本身要有上限：匿名来源可无限制造 key，若只增不删，进程内存会被慢慢吃掉。
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque

_LOCK = threading.Lock()
_HITS: dict[str, Deque[float]] = {}
#: key 表硬上限；超过先回收过期/空 key，仍满则淘汰最旧的一条
MAX_KEYS = 4096


def allow(key: str, limit: int, window_seconds: float = 3600.0, *, now: float | None = None) -> bool:
    if limit <= 0:
        return True
    current = time.time() if now is None else now
    with _LOCK:
        hits = _HITS.get(key)
        if hits is None:
            if len(_HITS) >= MAX_KEYS:
                _prune(current, window_seconds)
            hits = _HITS.setdefault(key, deque())
        while hits and current - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(current)
    return True


def _prune(current: float, window_seconds: float) -> None:
    """在持锁状态下调用：先清过期/空 key，仍达上限时淘汰最久未命中的 key。"""
    for key in [k for k, hits in _HITS.items() if not hits or current - hits[-1] > window_seconds]:
        _HITS.pop(key, None)
    while len(_HITS) >= MAX_KEYS:
        oldest = min(_HITS, key=lambda k: _HITS[k][-1] if _HITS[k] else current)
        _HITS.pop(oldest, None)


def reset() -> None:
    with _LOCK:
        _HITS.clear()
