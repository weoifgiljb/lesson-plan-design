# -*- coding: utf-8 -*-
"""Stop：递归校验工作区中的教案 JSON，并按配置处理审查报告缺口。"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import skill_scripts
from _runtime import run_python

sys.path.insert(0, str(skill_scripts()))
from lib import default_review_path, export_gate, load_json, load_review_report  # type: ignore

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "output",
    "dist",
    "build",
    ".tmp",
    ".dsh",
}
SKIP_PREFIXES = (".", "~$")


def _is_plan(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    return isinstance(data, dict) and "activityFlow" in data and "contentTitle" in data


def _review(path: Path) -> tuple[str, bool]:
    review_path = default_review_path(path)
    if not review_path.is_file():
        return "缺少当前教案的对抗审查报告", False
    try:
        gate = export_gate(load_json(path), load_review_report(review_path))
    except (OSError, ValueError, json.JSONDecodeError):
        return f"审查报告无法解析：{review_path.name}", False
    if gate["ok"]:
        return "审查门禁通过", True
    return "；".join(gate["reasons"]), False


def _plans(root: Path) -> list[Path]:
    plans: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in dirnames
            if name not in SKIP_DIRS and not name.startswith(SKIP_PREFIXES)
        ]
        for name in filenames:
            if not name.lower().endswith(".json"):
                continue
            path = Path(dirpath) / name
            try:
                if _is_plan(path):
                    plans.append(path)
            except OSError:
                continue
    return sorted(plans)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stop 教案质量门")
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("LPP_STOP_ROOT", str(Path.cwd()))))
    parser.add_argument(
        "--mode",
        choices=("warn", "fail"),
        default=os.environ.get("LPP_STOP_REVIEW_MODE", "warn"),
        help="审查报告缺失/过期时：warn 仅提示，fail 返回非 0",
    )
    parser.add_argument("--strict", action="store_true", help="等价于 --mode fail")
    args = parser.parse_args()
    mode = "fail" if args.strict else args.mode
    root = args.root.resolve()
    if not root.is_dir():
        print(json.dumps({"ok": False, "error": f"根目录不存在：{root}"}, ensure_ascii=False))
        return 2
    plans = _plans(root)
    if not plans:
        print(json.dumps({"ok": True, "mode": mode, "root": str(root), "count": 0, "message": "Stop：未发现教案 JSON，跳过质量门"}, ensure_ascii=False))
        return 0
    script = skill_scripts() / "validate.py"
    failed = False
    reports = []
    for path in plans:
        proc = run_python(script, [str(path)])
        note, review_ok = _review(path)
        if proc.returncode != 0 or (mode == "fail" and not review_ok):
            failed = True
        reports.append({
            "file": str(path.relative_to(root)),
            "code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "review": note,
            "reviewOk": review_ok,
        })
    print(json.dumps({"ok": not failed, "mode": mode, "root": str(root), "count": len(plans), "reports": reports}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
