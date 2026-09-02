# -*- coding: utf-8 -*-
"""导入本技能全部测试。运行：python test/index.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_export import TestExportDocxFormat  # noqa: F401
from test_parse import TestParseMarkdown  # noqa: F401
from test_render import TestRenderOoxml  # noqa: F401

if __name__ == "__main__":
    import unittest

    unittest.main()
