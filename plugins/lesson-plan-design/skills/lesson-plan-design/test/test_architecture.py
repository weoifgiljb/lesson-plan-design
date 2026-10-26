# -*- coding: utf-8 -*-
"""组件边界与模块体量契约。"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from support import SKILL_DIR

ROOT = SKILL_DIR.parents[3]
SCRIPT = ROOT / "scripts" / "check_architecture.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_architecture", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestArchitecture(unittest.TestCase):
    def test_domain_does_not_import_adapters(self) -> None:
        module = _load()
        self.assertTrue(module.analyze_source("from mcp_lesson import tools", "x.py"))
        self.assertTrue(module.analyze_source("import export_docx", "x.py"))
        self.assertFalse(module.analyze_source("from .model import empty_plan", "x.py"))

    def test_repo_architecture_is_clean(self) -> None:
        module = _load()
        self.assertEqual(module.scan(), [])

    def test_entrypoints_stay_thin(self) -> None:
        module = _load()
        for path, limit in module.HARD_LIMITS.items():
            self.assertLessEqual(len(path.read_text(encoding="utf-8").splitlines()), limit, path)
