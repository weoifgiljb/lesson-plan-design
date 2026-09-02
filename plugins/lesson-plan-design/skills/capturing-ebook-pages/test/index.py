# -*- coding: utf-8 -*-
"""导入本技能全部测试。运行：python test/index.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_adapters import TestAdapters  # noqa: F401
from test_pages import TestPageSpec  # noqa: F401
from test_playwright import TestPlaywrightCapture  # noqa: F401

if __name__ == "__main__":
    import unittest

    unittest.main()
