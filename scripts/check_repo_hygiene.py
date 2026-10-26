# -*- coding: utf-8 -*-
"""仓库卫生检查：已跟踪文件不得包含本机绝对用户路径。"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOWS_USER = re.compile(r"(?i)\b[A-Z]:[\\/]Users[\\/](?=[A-Za-z0-9_\u4e00-\u9fff])")
POSIX_USER = re.compile(r"/home/(?=[A-Za-z0-9_\u4e00-\u9fff])")
TEXT_SUFFIXES = {".py", ".md", ".json", ".toml", ".ps1", ".yaml", ".yml", ".txt", ".mdc"}


def check_text(text: str, label: str = "<text>") -> list[dict]:
    problems = []
    for number, line in enumerate(text.splitlines(), 1):
        for pattern, rule in ((WINDOWS_USER, "windows_user_path"), (POSIX_USER, "posix_user_path")):
            if pattern.search(line):
                problems.append({"file": label, "line": number, "rule": rule})
    return problems


def tracked_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git ls-files failed")
    return [ROOT / name for name in proc.stdout.split("\0") if name]


def check_repo() -> list[dict]:
    problems = []
    for path in tracked_files():
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        problems.extend(check_text(text, path.relative_to(ROOT).as_posix()))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="检查仓库中的本机绝对路径")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()
    problems = check_repo()
    payload = {"ok": not problems, "count": len(problems), "problems": problems}
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.json else None))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
