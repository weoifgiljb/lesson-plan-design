# -*- coding: utf-8 -*-
"""OPS 备份/恢复测试入口。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_backup_restore import TestBackupRestore  # noqa: E402,F401
from test_bootstrap_skills import TestBootstrapSkills  # noqa: E402,F401
from test_doctor import TestDoctor  # noqa: E402,F401

if __name__ == "__main__":
    import unittest

    unittest.main()
