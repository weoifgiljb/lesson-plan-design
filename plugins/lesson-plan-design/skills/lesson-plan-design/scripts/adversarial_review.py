# -*- coding: utf-8 -*-
"""创建、复审或教师放行校标教案的对抗审查报告。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (
    adversarial_review,
    default_review_path,
    dump,
    load_json,
    load_review_report,
    record_teacher_override,
    save_review_report,
)


def _finding(value: str | None) -> dict | None:
    if not value:
        return None
    path = Path(value)
    raw = path.read_text(encoding="utf-8") if path.is_file() else value
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("finding 必须是 JSON 对象或 JSON 文件路径")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="生成校标教案的对抗审查报告")
    parser.add_argument("path", help="教案 JSON 路径")
    parser.add_argument("--review", help="审查报告路径；默认与教案同目录")
    parser.add_argument("--round", type=int, help="复审轮次；必须等于上一轮+1，首轮为 1")
    parser.add_argument("--finding", help="审校 Agent 产出的单条 finding JSON 或其文件路径")
    parser.add_argument("--no-counterexample", action="store_true", help="审校员确认本轮无可证实反例")
    parser.add_argument("--reviewer-mode", choices=["native_subagent", "role_simulation"], default="role_simulation")
    parser.add_argument("--override", metavar="ISSUE_ID", help="教师放行的问题 ID")
    parser.add_argument("--teacher", help="教师姓名；与 --override 同用")
    parser.add_argument("--reason", help="放行原因；与 --override 同用")
    args = parser.parse_args()

    plan_path = Path(args.path)
    plan = load_json(plan_path)
    report_path = Path(args.review) if args.review else default_review_path(plan_path)
    previous = load_review_report(report_path) if report_path.is_file() else None

    if args.override:
        if not previous:
            parser.error("教师放行需要现有审查报告")
        try:
            override = record_teacher_override(
                previous, args.override, teacher=args.teacher or "", reason=args.reason or "", plan=plan,
            )
        except ValueError as exc:
            parser.error(str(exc))
        save_review_report(report_path, previous)
        print(dump({"ok": True, "path": str(report_path), "override": override, "reviewReport": previous}))
        return 0

    if args.finding and args.no_counterexample:
        parser.error("不能同时使用 --finding 与 --no-counterexample")

    round_number = args.round if args.round is not None else (int(previous.get("round", 0)) + 1 if previous else 1)
    try:
        report = adversarial_review(
            plan,
            round_number=round_number,
            finding=_finding(args.finding),
            reviewer=args.reviewer_mode,
            previous_report=previous,
            no_counterexample=args.no_counterexample,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    save_review_report(report_path, report)
    passed = report["status"] in {"passed", "passed_with_override"}
    print(dump({"ok": passed, "path": str(report_path), "reviewReport": report}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
