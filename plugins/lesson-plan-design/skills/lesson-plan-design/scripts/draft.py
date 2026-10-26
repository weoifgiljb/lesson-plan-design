# -*- coding: utf-8 -*-
"""根据周次/课次/课题草稿完整校标教案 JSON。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import JsonArgumentParser, run_cli
from lib import draft_plan, dump, validate_plan


def main() -> int:
    p = JsonArgumentParser(description="草稿校标教案")
    p.add_argument("--week", type=int, required=True)
    p.add_argument("--session", type=int, required=True)
    p.add_argument("--title", required=True, help="教学内容标题")
    p.add_argument("--detail", default="", help="教学内容补充，如练习套别")
    p.add_argument("--hours", type=float, default=2)
    p.add_argument("--year", default="2024-2025")
    p.add_argument("--semester", type=int, default=2, choices=[1, 2])
    p.add_argument("--teacher", default="")
    p.add_argument("--class", dest="teaching_object", default="")
    p.add_argument("--out", help="写出 JSON 路径；省略则打印到 stdout")
    args = p.parse_args()

    plan = draft_plan(
        args.week,
        args.session,
        args.title,
        content_detail=args.detail,
        planned_hours=args.hours,
        academic_year=args.year,
        semester=args.semester,
        teacher=args.teacher,
        teaching_object=args.teaching_object,
    )
    check = validate_plan(plan)
    if args.out:
        Path(args.out).write_text(dump(plan) + "\n", encoding="utf-8")
        print(dump({"ok": check["ok"], "path": args.out, "issues": check["issues"]}))
    else:
        print(dump(plan))
    return 0 if check["ok"] else 1


if __name__ == "__main__":
    sys.exit(run_cli(main))
