# -*- coding: utf-8 -*-
"""PostToolUse：若写入的是教案 JSON 则校验。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import skill_scripts
from _runtime import run_python


def _extract_path(payload: dict) -> str | None:
    for key in ("tool_input", "toolInput", "input"):
        block = payload.get(key)
        if isinstance(block, dict):
            for k in ("file_path", "filePath", "path"):
                val = block.get(k)
                if isinstance(val, str) and val:
                    return val
    for k in ("file_path", "filePath", "path"):
        val = payload.get(k)
        if isinstance(val, str) and val:
            return val
    return None


def main() -> int:
    raw = sys.stdin.read().strip()
    payload = {}
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
    path = _extract_path(payload)
    if not path or not path.lower().endswith(".json"):
        return 0
    target = Path(path)
    if not target.is_file():
        return 0
    # 只闸教案对象（含 activityFlow）
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(data, dict) or "activityFlow" not in data:
        return 0
    script = skill_scripts() / "validate.py"
    proc = run_python(script, [str(target)])
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        # 非 0 让宿主看到失败；部分 hook 实现 fail-open
        return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
