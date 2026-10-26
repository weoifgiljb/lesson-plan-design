# -*- coding: utf-8 -*-
"""样例库索引：生成或校验 examples/index.json。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import EXAMPLES_DIR, check_examples, dump, load_json, plan_hash

VERSION = "1.0"


def build_index(directory: Path) -> dict:
    examples = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "index.json":
            continue
        plan = load_json(path)
        examples.append({
            "file": path.name,
            "course": plan.get("course", ""),
            "week": plan.get("week"),
            "session": plan.get("session"),
            "contentTitle": plan.get("contentTitle", ""),
            "academicYear": plan.get("academicYear", ""),
            "semester": plan.get("semester"),
            "planHash": plan_hash(plan),
            "version": VERSION,
        })
    return {"schemaVersion": 1, "count": len(examples), "examples": examples}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成或校验 examples/index.json")
    parser.add_argument("--examples-dir", default=str(EXAMPLES_DIR), help="样例目录")
    parser.add_argument("--check", action="store_true", help="校验 index.json（默认）")
    parser.add_argument("--write", action="store_true", help="重新生成 index.json")
    args = parser.parse_args()
    directory = Path(args.examples_dir)
    if not directory.is_dir():
        print(dump({"ok": False, "errors": [f"样例目录不存在：{directory}"]}), file=sys.stderr)
        return 1
    if args.write:
        index = build_index(directory)
        index_path = directory / "index.json"
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result = check_examples(directory)
        result["written"] = str(index_path)
        print(dump(result))
        return 0 if result["ok"] else 1
    result = check_examples(directory)
    print(dump(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
