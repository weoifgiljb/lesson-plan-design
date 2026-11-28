# -*- coding: utf-8 -*-
"""内存限速器的窗口语义与 key 表上限（防匿名来源把进程内存打满）。"""
from __future__ import annotations

import unittest

from app.application import rate_limit


class TestRateLimit(unittest.TestCase):
    def setUp(self) -> None:
        rate_limit.reset()

    def tearDown(self) -> None:
        rate_limit.reset()

    def test_window_counts_and_recovers(self) -> None:
        self.assertTrue(rate_limit.allow("ip-1", 2, 60, now=100.0))
        self.assertTrue(rate_limit.allow("ip-1", 2, 60, now=101.0))
        self.assertFalse(rate_limit.allow("ip-1", 2, 60, now=102.0))
        # 窗口过期后重新放行
        self.assertTrue(rate_limit.allow("ip-1", 2, 60, now=200.0))
        # limit<=0 等于不限速
        self.assertTrue(rate_limit.allow("ip-2", 0))

    def test_key_table_is_bounded(self) -> None:
        now = 1_000_000.0
        for index in range(10_000):
            self.assertTrue(rate_limit.allow(f"k{index}", 1, 60, now=now))
        self.assertLessEqual(len(rate_limit._HITS), rate_limit.MAX_KEYS)

    def test_expired_keys_are_reclaimed_first(self) -> None:
        rate_limit.allow("stale", 5, 60, now=0.0)
        now = 10_000.0
        for index in range(rate_limit.MAX_KEYS + 10):
            rate_limit.allow(f"fresh{index}", 1, 60, now=now)
        self.assertNotIn("stale", rate_limit._HITS)
        self.assertLessEqual(len(rate_limit._HITS), rate_limit.MAX_KEYS)


if __name__ == "__main__":
    unittest.main()
