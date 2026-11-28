# -*- coding: utf-8 -*-
"""插件引擎对照：平台算出的哈希与校验结论必须与插件端一致。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import PLUGIN_EXAMPLES, plugin_lib, read_package_dir, load_json_bytes

from app.adapters import engine


class TestEngineParity(unittest.TestCase):
    def test_plan_hash_matches_plugin_for_examples(self) -> None:
        examples = sorted(path for path in PLUGIN_EXAMPLES.glob("*.json") if path.name != "index.json")
        self.assertEqual(len(examples), 15)
        for path in examples:
            plan = load_json_bytes(path.read_bytes())
            with self.subTest(example=path.name):
                self.assertEqual(engine.plan_hash(plan), plugin_lib.plan_hash(plan))

    def test_plan_hash_matches_plugin_for_fixture(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        self.assertEqual(engine.plan_hash(plan), plugin_lib.plan_hash(plan))

    def test_validation_matches_plugin(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        expected = plugin_lib.validate_plan(plan)
        actual = engine.validate_plan(plan)
        self.assertEqual(actual["ok"], expected["ok"])
        self.assertEqual(len(actual["issues"]), len(expected["issues"]))

    def test_engine_versions(self) -> None:
        versions = engine.engine_versions()
        self.assertEqual(versions["rulesVersion"], "1.1.0")
        self.assertEqual(versions["rubricVersion"], "1.0")
        self.assertNotIn("status", versions)

    def test_export_failure_keeps_existing_output(self) -> None:
        # 失败分支只能删 .tmp，不能顺手删掉已存在的旧 DOCX（可能是上一次成功产物）
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "plan.docx"
            output.mkdir()  # 目标是目录 → 原子替换必然失败，模拟导出失败
            result = engine.export_docx(plan, output)
            self.assertFalse(result["ok"])
            self.assertTrue(output.is_dir())
            self.assertFalse(output.with_name(output.name + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()
