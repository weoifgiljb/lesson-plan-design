# -*- coding: utf-8 -*-
"""一键运行插件端全部测试与契约 fixtures。"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design"
TEST = SKILL / "test"
FORMATTING = ROOT / "plugins" / "lesson-plan-design" / "skills" / "formatting-lesson-docx"
EBOOK = ROOT / "plugins" / "lesson-plan-design" / "skills" / "capturing-ebook-pages"
FIXTURES = ROOT / "tests" / "fixtures" / "dual-end" / "run_plugin_fixtures.py"
SYNC = SKILL / "scripts" / "sync_examples.py"
VALIDATE = SKILL / "scripts" / "validate.py"
LAYOUT = ROOT / "scripts" / "check_layout.py"
HYGIENE = ROOT / "scripts" / "check_repo_hygiene.py"
RAN_RE = re.compile(r"Ran (\d+) tests?")


def commands() -> list[dict]:
    items = [
        {"name": "lesson-plan unit", "cmd": [sys.executable, str(TEST / "index.py")]},
        {"name": "formatting docx", "cmd": [sys.executable, str(FORMATTING / "test" / "index.py")]},
        {"name": "ebook capture", "cmd": [sys.executable, str(EBOOK / "test" / "index.py")]},
        {"name": "gold examples", "cmd": [sys.executable, str(VALIDATE), "--examples"]},
    ]
    if SYNC.is_file():
        items.append({"name": "example index", "cmd": [sys.executable, str(SYNC), "--check"]})
    if FIXTURES.is_file():
        items.append({"name": "dual-end fixtures", "cmd": [sys.executable, str(FIXTURES)]})
    if LAYOUT.is_file():
        items.append({"name": "docx layout", "cmd": [sys.executable, str(LAYOUT)]})
    if HYGIENE.is_file():
        items.append({"name": "repo hygiene", "cmd": [sys.executable, str(HYGIENE)]})
    return items


def run_one(item: dict) -> dict:
    try:
        proc = subprocess.run(
            item["cmd"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        output = proc.stdout + proc.stderr
        match = RAN_RE.search(output)
        return {
            "name": item["name"],
            "ok": proc.returncode == 0,
            "exitCode": proc.returncode,
            "tests": int(match.group(1)) if match else 0,
            "output": output.strip()[-1500:],
        }
    except Exception as exc:  # noqa: BLE001 - 汇总时保留单项失败，不中断其他套件
        return {
            "name": item["name"],
            "ok": False,
            "exitCode": -1,
            "tests": 0,
            "output": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="一键运行插件端测试与 fixtures")
    parser.add_argument("--list", action="store_true", help="只列出将要运行的命令")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出汇总")
    parser.add_argument("--only", help="只运行名称包含该子串的套件")
    args = parser.parse_args()
    items = commands()
    if args.only:
        items = [item for item in items if args.only in item["name"]]
    if args.list:
        print(json.dumps({"commands": items}, ensure_ascii=False, indent=2))
        return 0
    results = [run_one(item) for item in items]
    payload = {
        "ok": all(item["ok"] for item in results),
        "commands": len(results),
        "tests": sum(item["tests"] for item in results),
        "failed": [item["name"] for item in results if not item["ok"]],
        "results": results,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for item in results:
            mark = "PASS" if item["ok"] else "FAIL"
            print(f"{mark}  {item['tests']:>3} tests  {item['name']}  (exit {item['exitCode']})")
            if not item["ok"]:
                print(item["output"])
        print(f"\n{payload['commands'] - len(payload['failed'])}/{payload['commands']} suites passed, "
              f"{payload['tests']} tests")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
