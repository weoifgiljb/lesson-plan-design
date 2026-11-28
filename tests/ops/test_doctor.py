# -*- coding: utf-8 -*-
"""OPS-06 / FR-17：体检脚本的清单、技能与命令一致性。"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import doctor  # noqa: E402


class TestDoctor(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.gettempdir()) / f"lpp-doctor-{uuid.uuid4().hex}"
        self.root.mkdir(mode=0o777)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_real_plugin_manifests_and_commands_are_consistent(self) -> None:
        result = doctor.check_plugin(doctor.DEFAULT_PLUGIN)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(len(result["manifests"]), 5)

    def test_real_docs_use_py3(self) -> None:
        result = doctor.check_doc_commands(doctor.DEFAULT_PLUGIN, doctor.ROOT / "docs")
        self.assertTrue(result["ok"], result["errors"])

    def test_doc_bare_python_is_reported(self) -> None:
        docs = self.root / "docs" / "setup"
        docs.mkdir(parents=True)
        (docs / "ide-setup.md").write_text("```bash\npython scripts/validate.py x.json\n```\n", encoding="utf-8")
        result = doctor.check_doc_commands(self.root / "plugin", self.root / "docs")
        self.assertFalse(result["ok"])
        self.assertIn("命令使用 python", "；".join(result["errors"]))

    def test_missing_skills_are_reported(self) -> None:
        result = doctor.check_skills(doctor.DEFAULT_LOCK, self.root / "skills")
        self.assertFalse(result["ok"])
        self.assertEqual(result["count"], 24)
        self.assertIn("技能缺失 24/24", "；".join(result["errors"]))

    def test_bare_python_command_is_reported(self) -> None:
        plugin = self.root / "plugin"
        (plugin / "skills").mkdir(parents=True)
        (plugin / "skills" / "SKILL.md").write_text("x", encoding="utf-8")
        for relative in doctor.PLUGIN_MANIFESTS:
            path = plugin / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {"name": "demo", "version": "1.0.0", "description": "demo", "skills": "./skills/"},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        (plugin / ".mcp.json").write_text(
            json.dumps({"mcpServers": {"demo": {"command": "python", "args": ["x.py"]}}}),
            encoding="utf-8",
        )
        result = doctor.check_plugin(plugin)
        self.assertFalse(result["ok"])
        self.assertIn("裸 python 命令", "；".join(result["errors"]))

    def test_missing_database_is_reported(self) -> None:
        result = doctor.check_data(self.root, self.root / "backups")
        self.assertFalse(result["ok"])
        self.assertIn("app.db", "；".join(result["errors"]))


if __name__ == "__main__":
    unittest.main()
