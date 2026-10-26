# -*- coding: utf-8 -*-
"""统一解释器解析与 UTF-8 子进程边界。"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from functools import lru_cache

OVERRIDE_ENV = ("LPP_PYTHON", "LESSON_PLAN_PYTHON")


def utf8_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """返回强制 UTF-8 的环境变量副本。"""
    env = dict(base or os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _candidates():
    for key in OVERRIDE_ENV:
        value = os.environ.get(key, "").strip()
        if value:
            if os.path.isfile(value):
                yield [value]
            else:
                yield shlex.split(value)
            break
    yield [sys.executable]
    for name in ("python", "python3"):
        path = shutil.which(name)
        if path:
            yield [path]
    if shutil.which("py"):
        yield ["py", "-3"]


@lru_cache(maxsize=1)
def resolve_python() -> tuple[str, ...]:
    """按覆盖变量、当前解释器、python、py -3 的顺序探测并缓存。"""
    for command in _candidates():
        if not command:
            continue
        try:
            probe = subprocess.run(
                [*command, "-c", "import sys"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=utf8_env(),
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return tuple(command)
    return (sys.executable,)


def run_python(
    script,
    args: list[str] | None = None,
    *,
    cwd=None,
    input_text: str | None = None,
    timeout: float | None = 120,
) -> subprocess.CompletedProcess:
    """用解析出的解释器执行脚本，统一 UTF-8 解码并记录替换。"""
    command = [*resolve_python(), str(script), *(args or [])]
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=utf8_env(),
        cwd=cwd,
        input=input_text,
        timeout=timeout,
    )
    if "\ufffd" in (proc.stdout or "") or "\ufffd" in (proc.stderr or ""):
        sys.stderr.write("警告：子进程输出包含不可解码字符，已按替换处理\n")
    return proc
