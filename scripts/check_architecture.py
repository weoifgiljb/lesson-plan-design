# -*- coding: utf-8 -*-
"""组件边界检查：domain 不反向依赖 adapter，关键入口保持薄。"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "scripts"
DOMAIN = SCRIPTS / "lesson_plan"
FORBIDDEN_DOMAIN_IMPORTS = {"lib", "mcp_lesson", "docx_export", "export_docx", "subprocess"}
HARD_LIMITS = {
    ROOT / "plugins" / "lesson-plan-design" / "scripts" / "mcp_server.py": 80,
    SCRIPTS / "lib.py": 150,
    SCRIPTS / "export_docx.py": 250,
}


def _roots(source: str) -> set[str]:
    tree = ast.parse(source)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def analyze_source(source: str, filename: str = "<source>") -> list[dict]:
    problems = []
    for name in sorted(_roots(source) & FORBIDDEN_DOMAIN_IMPORTS):
        problems.append({"file": filename, "rule": "forbidden_import", "detail": name})
    return problems


def scan() -> list[dict]:
    problems: list[dict] = []
    if DOMAIN.is_dir():
        for path in sorted(DOMAIN.glob("*.py")):
            try:
                problems.extend(analyze_source(path.read_text(encoding="utf-8"), path.name))
            except (OSError, SyntaxError) as exc:
                problems.append({"file": path.name, "rule": "unreadable", "detail": str(exc)})
    for path, limit in HARD_LIMITS.items():
        if not path.is_file():
            continue
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count > limit:
            problems.append({
                "file": path.relative_to(ROOT).as_posix(),
                "rule": "module_too_large",
                "detail": f"{count} > {limit}",
            })
    return problems


def main() -> int:
    problems = scan()
    print(json.dumps({"ok": not problems, "count": len(problems), "problems": problems}, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
