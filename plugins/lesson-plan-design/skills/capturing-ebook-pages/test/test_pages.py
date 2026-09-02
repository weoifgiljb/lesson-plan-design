# -*- coding: utf-8 -*-
"""--pages 解析。"""
from __future__ import annotations

import unittest

from support import SCRIPTS_DIR  # noqa: F401
from capture_ebook import CaptureError, parse_pages


class TestPageSpec(unittest.TestCase):
    def test_all_pages_when_empty(self) -> None:
        self.assertEqual(parse_pages(None, 4), [1, 2, 3, 4])

    def test_range_and_list(self) -> None:
        self.assertEqual(parse_pages("3-7", 10), [3, 4, 5, 6, 7])
        self.assertEqual(parse_pages("1,3,5", 5), [1, 3, 5])
        self.assertEqual(parse_pages("2-4,7", 7), [2, 3, 4, 7])

    def test_out_of_range_raises(self) -> None:
        with self.assertRaises(CaptureError):
            parse_pages("9-12", 3)
