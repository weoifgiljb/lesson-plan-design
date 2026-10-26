# -*- coding: utf-8 -*-
"""解释器解析、UTF-8 子进程边界与命令配置一致性。"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from support import PLUGIN_ROOT  # noqa: F401  # 先把 scripts 加入 sys.path
from _runtime import resolve_python, run_python, utf8_env


class TestRuntime(unittest.TestCase):
    def test_utf8_env_sets_flags(self) -> None:
        env = utf8_env({"PATH": "x"})
        self.assertEqual(env["PYTHONUTF8"], "1")
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")
        self.assertEqual(env["PATH"], "x")

    def test_resolve_python_honours_override(self) -> None:
        with mock.patch.dict(os.environ, {"LPP_PYTHON": sys.executable}, clear=False):
            resolve_python.cache_clear()
            try:
                self.assertEqual(resolve_python()[0], sys.executable)
            finally:
                resolve_python.cache_clear()

    def test_resolve_python_returns_runnable_command(self) -> None:
        resolve_python.cache_clear()
        command = resolve_python()
        self.assertTrue(command)
        self.assertTrue(
            Path(command[0]).exists() or command[0] in {"python", "python3", "py"},
            command,
        )

    def test_run_python_decodes_chinese(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "say.py"
            script.write_text("import sys\nsys.stdout.write('中文')\n", encoding="utf-8")
            proc = run_python(script)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("中文", proc.stdout)

    def test_run_python_replaces_undecodable_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "bad.py"
            script.write_text(
                "import sys\nsys.stdout.buffer.write(b'\\xb2')\n",
                encoding="utf-8",
            )
            proc = run_python(script)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("\ufffd", proc.stdout)

    def test_hooks_and_mcp_configs_use_py_launcher(self) -> None:
        hooks = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for groups in hooks["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        self.assertTrue(commands)
        for command in commands:
            self.assertTrue(command.startswith("py -3 "), command)
        for path in (PLUGIN_ROOT / ".mcp.json", PLUGIN_ROOT / "mcp.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            server = data["mcpServers"]["lesson-plan"]
            self.assertEqual(server["command"], "py", path.name)
            self.assertEqual(server["args"][0], "-3", path.name)

    def test_skill_docs_use_py_launcher(self) -> None:
        skill_path = PLUGIN_ROOT / "skills" / "lesson-plan-design" / "SKILL.md"
        command_path = PLUGIN_ROOT / "commands" / "write-lesson-plan.md"
        readme_path = PLUGIN_ROOT / "README.md"
        for path in (skill_path, command_path, readme_path):
            text = path.read_text(encoding="utf-8")
            self.assertIn("py -3", text, path.name)
            self.assertIsNone(
                re.search(r"\bpython (scripts|skills|\.\.)", text),
                f"{path.name} 仍含旧命令",
            )
