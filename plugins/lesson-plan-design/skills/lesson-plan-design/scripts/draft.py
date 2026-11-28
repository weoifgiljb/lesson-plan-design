# -*- coding: utf-8 -*-
"""根据周次/课次/课题草稿完整校标教案 JSON。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import JsonArgumentParser, run_cli
from lib import draft_plan, dump, match_c_language_template, practice_sets, validate_plan


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
    p.add_argument("--plan-number", default="")
    p.add_argument("--teach-date", default="")
    p.add_argument("--student-context", default="")
    p.add_argument("--must-do", default="")
    p.add_argument("--optional", default="")
    p.add_argument("--out", help="写出 JSON 路径；省略则打印到 stdout")
    args = p.parse_args()
    _, tied = match_c_language_template(args.title)
    if tied:
        print(
            json.dumps(
                {
                    "ok": True,
                    "warnings": [f"模板匹配同分，请确认课题：{' / '.join(tied)}"],
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
    sample_must, sample_optional = practice_sets(args.week, args.session)
    if not (args.must_do or sample_must) or not (args.optional or sample_optional):
        print(
            json.dumps(
                {
                    "ok": True,
                    "warnings": [
                        "未匹配到同周次/课次样例，练习套别使用默认值："
                        f"必须完成={args.must_do or sample_must or '第1套'}，"
                        f"选做={args.optional or sample_optional or '第2套'}"
                    ],
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )

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
        teach_date=args.teach_date,
        plan_number=args.plan_number,
        student_context=args.student_context,
        must_do=args.must_do or None,
        optional=args.optional or None,
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
