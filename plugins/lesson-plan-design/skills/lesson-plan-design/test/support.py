# -*- coding: utf-8 -*-
"""教案技能测试共用路径与 MCP 加载。"""
from __future__ import annotations

import contextlib
import importlib.util
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SKILL_DIR = TEST_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
PLUGIN_ROOT = SKILL_DIR.parents[1]
PLUGIN_SCRIPTS_DIR = PLUGIN_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(PLUGIN_SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(PLUGIN_SCRIPTS_DIR))


def utf8_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


@contextlib.contextmanager
def tempdir():
    """创建可清理的临时目录，替代 ``tempfile.TemporaryDirectory``。

    ``TemporaryDirectory`` 用 0700 建目录，在 Windows 沙箱与部分杀软环境下
    该目录随后会被判为不可写，清理阶段也会因删除锁失败抛 ``PermissionError``。
    这里显式用 0o777 建目录，清理失败只忽略、不改变测试结论。
    """
    root = Path(tempfile.gettempdir()) / f"lpp-test-{uuid.uuid4().hex}"
    root.mkdir(mode=0o777)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def load_mcp(name: str):
    mcp_path = PLUGIN_ROOT / "scripts" / "mcp_server.py"
    spec = importlib.util.spec_from_file_location(name, mcp_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module
