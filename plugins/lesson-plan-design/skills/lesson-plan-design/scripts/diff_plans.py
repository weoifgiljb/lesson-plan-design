# -*- coding: utf-8 -*-
"""输出两版教案的字段级差异。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import JsonArgumentParser, run_cli
from lib import dump, load_json


def _diff(left: Any, right: Any, prefix: str, changes: list[dict[str, Any]]) -> None:
    if type(left) is not type(right):
        changes.append({"path": prefix or "$", "before": left, "after": right})
        return
    if isinstance(left, dict):
        for key in sorted(set(left) | set(right)):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in left:
                changes.append({"path": path, "before": None, "after": right[key]})
            elif key not in right:
                changes.append({"path": path, "before": left[key], "after": None})
            else:
                _diff(left[key], right[key], path, changes)
        return
    if isinstance(left, list):
        for index in range(max(len(left), len(right))):
            path = f"{prefix}[{index}]"
            if index >= len(left):
                changes.append({"path": path, "before": None, "after": right[index]})
            elif index >= len(right):
                changes.append({"path": path, "before": left[index], "after": None})
            else:
                _diff(left[index], right[index], path, changes)
        return
    if left != right:
        changes.append({"path": prefix or "$", "before": left, "after": right})


def main() -> int:
    parser = JsonArgumentParser(description="比较两版教案 JSON")
    parser.add_argument("left", help="旧版教案 JSON")
    parser.add_argument("right", help="新版教案 JSON")
    args = parser.parse_args()
    changes: list[dict[str, Any]] = []
    _diff(load_json(Path(args.left)), load_json(Path(args.right)), "", changes)
    print(dump({"ok": True, "count": len(changes), "changes": changes}))
    return 0


if __name__ == "__main__":
    sys.exit(run_cli(main))
