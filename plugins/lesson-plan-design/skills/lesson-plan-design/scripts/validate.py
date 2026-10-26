# -*- coding: utf-8 -*-
"""校验校标教案 JSON。退出码 0 合格，1 不合格。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import RULES_VERSION, dump, load_examples, load_json, validate_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="校验校标教案 JSON")
    parser.add_argument("path", nargs="?", help="教案 JSON 路径")
    parser.add_argument("--examples", action="store_true", help="校验 examples/ 全部金标准")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读 JSON")
    parser.add_argument("--strict", action="store_true", help="目录课题/套别冲突按错误处理")
    parser.add_argument(
        "--minutes-tolerance",
        type=float,
        default=0.0,
        help="活动分钟合计容差，默认 0",
    )
    args = parser.parse_args()

    if args.examples:
        items = load_examples()
        if not items:
            print(dump({"ok": False, "issues": [{"path": "examples", "message": "未找到 examples/*.json"}]}))
            return 1
        all_ok = True
        reports = []
        for path, plan in items:
            result = validate_plan(
                plan,
                strict=args.strict,
                minutes_tolerance=args.minutes_tolerance,
            )
            reports.append(
                {
                    "file": path.name,
                    "ok": result["ok"],
                    "issues": result["issues"],
                    "warnings": result["warnings"],
                }
            )
            if not result["ok"]:
                all_ok = False
        print(dump({"ok": all_ok, "ruleVersion": RULES_VERSION, "reports": reports}))
        return 0 if all_ok else 1

    if args.stdin:
        data = json.load(sys.stdin)
    elif args.path:
        data = load_json(Path(args.path))
    else:
        parser.error("请提供教案 JSON 路径，或使用 --examples / --stdin")
        return 2

    result = validate_plan(
        data,
        strict=args.strict,
        minutes_tolerance=args.minutes_tolerance,
    )
    print(dump({k: v for k, v in result.items() if k != "plan"}))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
