# -*- coding: utf-8 -*-
"""仓库卫生检查：绝对用户路径与占位符。"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from support import SKILL_DIR

ROOT = SKILL_DIR.parents[3]
SCRIPT = ROOT / "scripts" / "check_repo_hygiene.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_repo_hygiene", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestHygiene(unittest.TestCase):
    def test_windows_absolute_user_path_is_detected(self) -> None:
        module = _load()
        bad = "C:" + "/Users/" + "alice" + "/repo/plan.py"
        self.assertTrue(module.check_text(bad))

    def test_placeholder_path_is_allowed(self) -> None:
        module = _load()
        good = "C:" + "/Users/" + "<user>" + "/repo/plan.py"
        self.assertFalse(module.check_text(good))

    def test_tracked_repo_has_no_absolute_user_paths(self) -> None:
        module = _load()
        self.assertEqual(module.check_repo(), [])
