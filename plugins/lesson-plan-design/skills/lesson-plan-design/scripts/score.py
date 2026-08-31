# -*- coding: utf-8 -*-
"""对照 examples 给教案打结构分。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import dump, load_json, score_against_examples


def main() -> int:
    p = argparse.ArgumentParser(description="对照 examples 评分")
    p.add_argument("path", nargs="?", help="教案 JSON")
    p.add_argument("--stdin", action="store_true")
    args = p.parse_args()
    if args.stdin:
        plan = json.load(sys.stdin)
    elif args.path:
        plan = load_json(Path(args.path))
    else:
        p.error("请提供教案 JSON")
        return 2
    print(dump(score_against_examples(plan)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
