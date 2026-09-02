# -*- coding: utf-8 -*-
"""导入本技能全部测试。运行：python test/index.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_cli import TestCli  # noqa: F401
from test_docs import TestDocs  # noqa: F401
from test_export_gate import TestExportGate  # noqa: F401
from test_hooks import TestHooks  # noqa: F401
from test_mcp import TestMcp  # noqa: F401
from test_review import TestReview  # noqa: F401
from test_validate import TestValidate  # noqa: F401

if __name__ == "__main__":
    import unittest

    unittest.main()
