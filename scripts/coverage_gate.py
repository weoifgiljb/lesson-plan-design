# -*- coding: utf-8 -*-
"""无第三方依赖的核心模块覆盖率门禁。

统计范围：插件 `lesson_plan/` 领域模块、`lib.py` 与 `_runtime.py`。CLI/MCP 入口
由子进程执行，不计入本报告；它们的契约由 test_cli/test_mcp 覆盖。
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "lesson-plan-design"
SCRIPTS = PLUGIN / "skills" / "lesson-plan-design" / "scripts"
TESTS = PLUGIN / "skills" / "lesson-plan-design" / "test"
THRESHOLD = 80.0


def _target_files() -> list[Path]:
    files = sorted((SCRIPTS / "lesson_plan").glob("*.py"))
    for name in ("lib.py", "_runtime.py"):
        path = SCRIPTS / name
        if path.is_file():
            files.append(path)
    return files


def _executable_lines(path: Path) -> set[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            lines.add(int(node.lineno))
    return lines


def _run_tests() -> dict[str, Any]:
    sys.path.insert(0, str(TESTS))
    suite = unittest.TestLoader().discover(str(TESTS), pattern="test_*.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    return {
        "run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
    }


def measure(threshold: float = THRESHOLD) -> dict[str, Any]:
    targets = _target_files()
    resolved = {path.resolve() for path in targets}
    hits: dict[Path, set[int]] = {path: set() for path in targets}
    executable = {path: _executable_lines(path) for path in targets}

    def tracer(frame, event, _arg):
        if event == "line":
            filename = Path(frame.f_code.co_filename).resolve()
            if filename in resolved:
                hits[filename].add(int(frame.f_lineno))
        return tracer

    sys.settrace(tracer)
    try:
        tests = _run_tests()
    finally:
        sys.settrace(None)

    files: list[dict[str, Any]] = []
    covered = 0
    statements = 0
    for path in targets:
        total = len(executable[path])
        hit = len(hits[path] & executable[path])
        covered += hit
        statements += total
        files.append(
            {
                "file": path.relative_to(SCRIPTS).as_posix(),
                "covered": hit,
                "statements": total,
                "percent": round(100.0 * hit / total, 1) if total else 100.0,
            }
        )
    percent = round(100.0 * covered / statements, 1) if statements else 100.0
    return {
        "ok": percent >= threshold and tests["failures"] == 0 and tests["errors"] == 0,
        "threshold": threshold,
        "totals": {"covered": covered, "statements": statements, "percent": percent},
        "files": files,
        "tests": tests,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="核心模块覆盖率门禁（标准库实现）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--json-out", type=Path, default=None, help="同时写入 JSON 报告")
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    args = parser.parse_args()
    report = measure(threshold=args.threshold)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["files"]:
            print(f"{item['percent']:5.1f}%  {item['file']:40s} {item['covered']:4d}/{item['statements']:4d}")
        total = report["totals"]
        print(f"\ncore coverage: {total['percent']:.1f}% ({total['covered']}/{total['statements']}), threshold {report['threshold']:.0f}%")
        print(f"tests: run={report['tests']['run']} failures={report['tests']['failures']} errors={report['tests']['errors']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
