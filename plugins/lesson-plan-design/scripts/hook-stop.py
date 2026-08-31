# -*- coding: utf-8 -*-
"""Stop：校验工作区中的教案 JSON（activityFlow），没有则放行。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import skill_scripts

CANDIDATE_GLOBS = ("*.json", "output/*.json", "教案*.json")


def _is_plan(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    return isinstance(data, dict) and "activityFlow" in data and "contentTitle" in data


def main() -> int:
    cwd = Path.cwd()
    files: list[Path] = []
    for pattern in CANDIDATE_GLOBS:
        files.extend(p for p in cwd.glob(pattern) if p.is_file())
    plans = []
    seen = set()
    for path in files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if _is_plan(path):
            plans.append(path)
    if not plans:
        print(json.dumps({"ok": True, "message": "Stop：未发现教案 JSON，跳过质量门"}, ensure_ascii=False))
        return 0
    script = skill_scripts() / "validate.py"
    failed = False
    reports = []
    for path in plans[:8]:
        proc = subprocess.run(
            [sys.executable, str(script), str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        reports.append({"file": str(path), "code": proc.returncode, "stdout": proc.stdout.strip()})
        if proc.returncode != 0:
            failed = True
    print(json.dumps({"ok": not failed, "reports": reports}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
