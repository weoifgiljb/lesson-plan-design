# -*- coding: utf-8 -*-
"""教案技能测试共用路径与 MCP 加载。"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SKILL_DIR = TEST_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
PLUGIN_ROOT = SKILL_DIR.parents[1]

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def utf8_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def load_mcp(name: str):
    mcp_path = PLUGIN_ROOT / "scripts" / "mcp_server.py"
    spec = importlib.util.spec_from_file_location(name, mcp_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module
