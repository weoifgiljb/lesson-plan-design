# -*- coding: utf-8 -*-
"""测试清单：每个 test_*.py 都必须被 index.py 导入，一键 runner 可发现。"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from support import SKILL_DIR, TEST_DIR

ROOT = SKILL_DIR.parents[3]


class TestManifest(unittest.TestCase):
    def test_all_test_modules_are_imported_by_index(self) -> None:
        modules = {path.stem for path in TEST_DIR.glob("test_*.py")}
        index = (TEST_DIR / "index.py").read_text(encoding="utf-8")
        for module in sorted(modules):
            self.assertIn(f"from {module} import", index, module)

    def test_every_test_file_has_cases(self) -> None:
        for path in TEST_DIR.glob("test_*.py"):
            self.assertIn("unittest.TestCase", path.read_text(encoding="utf-8"), path.name)

    def test_runner_lists_all_suites(self) -> None:
        runner = ROOT / "scripts" / "run_all_tests.py"
        proc = subprocess.run(
            [sys.executable, str(runner), "--list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        names = [item["name"] for item in data["commands"]]
        self.assertIn("lesson-plan unit", names)
        self.assertIn("dual-end fixtures", names)
        self.assertTrue(all(isinstance(item["cmd"], list) for item in data["commands"]))
