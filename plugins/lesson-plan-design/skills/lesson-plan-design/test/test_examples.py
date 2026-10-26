# -*- coding: utf-8 -*-
"""样例库索引同步与哈希校验。"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import SCRIPTS_DIR, utf8_env
from lib import EXAMPLES_DIR, check_examples, load_examples, plan_hash


class TestExamplesIndex(unittest.TestCase):
    def test_committed_index_is_current(self) -> None:
        result = check_examples()
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["count"], 7)

    def test_load_examples_excludes_index(self) -> None:
        items = load_examples()
        self.assertEqual(len(items), 7)
        self.assertTrue(all(path.name != "index.json" for path, _plan in items))

    def test_index_entries_carry_hash_and_metadata(self) -> None:
        index = json.loads((EXAMPLES_DIR / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["count"], 7)
        for item in index["examples"]:
            plan = json.loads((EXAMPLES_DIR / item["file"]).read_text(encoding="utf-8"))
            self.assertEqual(item["planHash"], plan_hash(plan))
            self.assertEqual(item["contentTitle"], plan.get("contentTitle"))
            self.assertEqual(item["week"], plan.get("week"))
            self.assertEqual(item["session"], plan.get("session"))

    def test_stale_hash_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in EXAMPLES_DIR.glob("*.json"):
                shutil.copy2(path, root / path.name)
            target = next(root.glob("信息技术*.json"))
            plan = json.loads(target.read_text(encoding="utf-8"))
            plan["contentTitle"] = "已改标题"
            target.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            result = check_examples(root)
        self.assertFalse(result["ok"])
        self.assertIn(target.name, result["stale"])

    def test_missing_index_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in EXAMPLES_DIR.glob("*.json"):
                if path.name != "index.json":
                    shutil.copy2(path, root / path.name)
            result = check_examples(root)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["missing"]), 7)

    def test_sync_write_then_check(self) -> None:
        script = SCRIPTS_DIR / "sync_examples.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in EXAMPLES_DIR.glob("*.json"):
                if path.name != "index.json":
                    shutil.copy2(path, root / path.name)
            written = subprocess.run(
                [sys.executable, str(script), "--examples-dir", str(root), "--write"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=utf8_env(),
            )
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertTrue((root / "index.json").is_file())
            checked = subprocess.run(
                [sys.executable, str(script), "--examples-dir", str(root), "--check"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=utf8_env(),
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            target = next(root.glob("信息技术*.json"))
            plan = json.loads(target.read_text(encoding="utf-8"))
            plan["contentTitle"] = "已改标题"
            target.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            stale = subprocess.run(
                [sys.executable, str(script), "--examples-dir", str(root), "--check"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=utf8_env(),
            )
            self.assertEqual(stale.returncode, 1)
            self.assertIn(target.name, stale.stdout)
