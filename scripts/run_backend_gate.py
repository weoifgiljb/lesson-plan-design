# -*- coding: utf-8 -*-
"""后端闸门聚合入口：架构 → 契约 → 安全 → 后端测试。

用法：
    py -3 scripts/run_backend_gate.py
    py -3 scripts/run_backend_gate.py --json
    py -3 scripts/run_backend_gate.py --only contract
    py -3 scripts/run_backend_gate.py --update-contract

`src/backend` 不存在时整组 skip 并返回 0，保证后端未开工时全量 runner 不空转。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gate_common as common  # noqa: E402

CHECKS = (
    ("architecture", "check_backend_architecture.py"),
    ("contract", "check_backend_contract.py"),
    ("security", "check_backend_security.py"),
)
TEST_INDEX = common.BACKEND / "tests" / "index.py"
RAN_RE = re.compile(r"Ran (\d+) tests?")


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run_check(name: str, script: str) -> dict:
    path = Path(__file__).resolve().parent / script
    proc = subprocess.run(
        [sys.executable, str(path), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(),
        cwd=common.ROOT,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "gate": name,
            "ok": False,
            "skipped": False,
            "blocks": [
                common.problem("GATE", script, 0, f"闸门输出不是 JSON：{proc.stdout.strip()[:200]}{proc.stderr.strip()[:200]}")
            ],
            "warns": [],
        }
    payload.setdefault("blocks", [])
    payload.setdefault("warns", [])
    payload["ok"] = bool(payload.get("ok"))
    return payload


def run_tests() -> dict:
    if not TEST_INDEX.is_file():
        return {"name": "backend tests", "ok": True, "skipped": True, "tests": 0, "output": ""}
    proc = subprocess.run(
        [sys.executable, str(TEST_INDEX)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(),
        cwd=common.ROOT,
    )
    output = (proc.stdout + proc.stderr).strip()
    match = RAN_RE.search(output)
    return {
        "name": "backend tests",
        "ok": proc.returncode == 0,
        "skipped": False,
        "tests": int(match.group(1)) if match else 0,
        "output": output[-2000:],
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="后端闸门：架构 + 契约 + 安全 + 测试")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--only", choices=[name for name, _ in CHECKS] + ["tests"], help="只跑某一项")
    parser.add_argument("--update-contract", action="store_true", help="刷新 OpenAPI 快照后退出")
    args = parser.parse_args()

    if args.update_contract:
        script = Path(__file__).resolve().parent / "check_backend_contract.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--update-contract"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_env(),
            cwd=common.ROOT,
        )
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode

    skipped = not common.BACKEND.is_dir()
    selected = [item for item in CHECKS if not args.only or item[0] == args.only]
    tests_skipped = args.only not in (None, "tests")
    checks = [] if skipped else [run_check(name, script) for name, script in selected]
    tests = {"name": "backend tests", "ok": True, "skipped": True, "tests": 0, "output": ""}
    if not skipped and not tests_skipped:
        tests = run_tests()

    blocks = [item for check in checks for item in check.get("blocks", [])]
    warns = [item for check in checks for item in check.get("warns", [])]
    ok = not blocks and tests.get("ok", True)
    payload = {
        "gate": "backend",
        "ok": ok,
        "skipped": skipped,
        "checks": checks,
        "tests": tests,
        "blocks": len(blocks),
        "warns": len(warns),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif skipped:
        print("SKIP  backend gate（未发现 src/backend，后端尚未开工）")
    else:
        for check in checks:
            mark = "SKIP" if check.get("skipped") else ("PASS" if check.get("ok") else "FAIL")
            print(f"{mark}  {check['gate']}: block {len(check.get('blocks', []))}，warn {len(check.get('warns', []))}")
            for item in check.get("blocks", []) + check.get("warns", []):
                print(f"      {item['severity']:<5} {item['rule']}  {item['file']}:{item['line']}  {item['detail']}")
        test_mark = "SKIP" if tests.get("skipped") else ("PASS" if tests.get("ok") else "FAIL")
        print(f"{test_mark}  backend tests: {tests.get('tests', 0)} tests")
        if not tests.get("ok"):
            print(tests.get("output", ""))
        print(f"{'OK' if ok else 'FAIL'}  backend gate：block {len(blocks)}，warn {len(warns)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
