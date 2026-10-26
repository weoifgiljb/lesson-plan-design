# -*- coding: utf-8 -*-
"""导入闸门自测。运行：py -3 tests/gate/index.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_gates import (  # noqa: E402,F401
    TestArchitectureGate,
    TestContractGate,
    TestGateRunner,
    TestSecurityGate,
)

if __name__ == "__main__":
    import unittest

    unittest.main()
