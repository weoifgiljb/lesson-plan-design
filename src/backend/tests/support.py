# -*- coding: utf-8 -*-
"""后端测试共用夹具：临时数据目录、fixtures 读取、插件端对照。"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
BACKEND = TEST_DIR.parent
REPO_ROOT = BACKEND.parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "dual-end"
PLUGIN_SCRIPTS = REPO_ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "scripts"
PLUGIN_EXAMPLES = REPO_ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "examples"

for candidate in (BACKEND, PLUGIN_SCRIPTS):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import lib as plugin_lib  # noqa: E402 - 插件端对照实现


@contextlib.contextmanager
def tempdir():
    """沙箱安全的临时目录（0777 + 清理失败忽略）。"""
    root = Path(tempfile.gettempdir()) / f"lpp-backend-{uuid.uuid4().hex}"
    root.mkdir(mode=0o777)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


@contextlib.contextmanager
def isolated_data_dir(root: Path):
    previous = os.environ.get("LPP_DATA_DIR")
    os.environ["LPP_DATA_DIR"] = str(root)
    try:
        yield root
    finally:
        if previous is None:
            os.environ.pop("LPP_DATA_DIR", None)
        else:
            os.environ["LPP_DATA_DIR"] = previous


def fixture_dir(kind: str, name: str) -> Path:
    return FIXTURES / "platform" / name if kind == "package" else FIXTURES / kind / name


def read_tree(base: Path) -> dict[str, bytes]:
    return {
        path.relative_to(base).as_posix(): path.read_bytes()
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def read_package_dir(name: str) -> dict[str, bytes]:
    return read_tree(FIXTURES / "platform" / name)


def package_zip(name: str) -> bytes:
    return (FIXTURES / "platform" / "packages" / name).read_bytes()


def expected_platform() -> dict:
    return json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))["platform"]


def load_json_bytes(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8"))


def plugin_report(plan: dict, *, round_number: int = 1, previous_report: dict | None = None) -> dict:
    return plugin_lib.adversarial_review(
        plan,
        round_number=round_number,
        previous_report=previous_report,
        reviewer="native_subagent",
        no_counterexample=True,
    )
