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
#: 上次全表过期清理的时间：表满时每个新 key 都触发一次全表扫描会把锁占满
_last_prune = 0.0


def allow(key: str, limit: int, window_seconds: float = 3600.0, *, now: float | None = None) -> bool:
    if limit <= 0:
        return True
    current = time.time() if now is None else now
    with _LOCK:
        return _register(key, limit, window_seconds, current)


def _register(key: str, limit: int, window_seconds: float, current: float) -> bool:
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
    """在持锁状态下调用：过期清理最多每个窗口一次，其余情况只做 O(1) 淘汰。

    取舍：不做"最久未命中"的精确淘汰——那需要在锁内全表扫描，而触发场景恰好是
    匿名来源刷 key 的攻击流量；这里只要内存有界且锁不被长期占住即可。
    """
    global _last_prune
    if current - _last_prune >= window_seconds:
        _last_prune = current
        for key in [
            k for k, hits in _HITS.items() if not hits or current - hits[-1] > window_seconds
        ]:
            _HITS.pop(key, None)
    while len(_HITS) >= MAX_KEYS and _HITS:
        _HITS.pop(next(iter(_HITS)))


def reset() -> None:
    global _last_prune
    with _LOCK:
        _HITS.clear()
        _last_prune = 0.0
