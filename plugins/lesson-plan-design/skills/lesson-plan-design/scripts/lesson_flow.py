# -*- coding: utf-8 -*-
"""一键流程：草稿 → 校验 → 审校 → 导出；支持 --until 断点与 --plan 续跑。"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import CliError, JsonArgumentParser, run_cli
from export_docx import export_docx
from lib import (
    adversarial_review,
    default_review_path,
    draft_plan,
    dump,
    load_json,
    save_review_report,
    validate_plan,
)


def _safe(value: str) -> str:
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "").strip())
    return re.sub(r"\s+", " ", text).strip(" .")[:40] or "未命名课题"


def main() -> int:
    parser = JsonArgumentParser(description="一键教案流程")
    parser.add_argument("--plan", help="已有教案 JSON；省略则从 --week/--session/--title 草稿")
    parser.add_argument("--week", type=int)
    parser.add_argument("--session", type=int)
    parser.add_argument("--title")
    parser.add_argument("--detail", default="")
    parser.add_argument("--hours", type=float, default=2)
    parser.add_argument("--year", default="2024-2025")
    parser.add_argument("--semester", type=int, default=2, choices=[1, 2])
    parser.add_argument("--teacher", default="")
    parser.add_argument("--class", dest="teaching_object", default="")
    parser.add_argument("--plan-number", default="")
    parser.add_argument("--teach-date", default="")
    parser.add_argument("--student-context", default="")
    parser.add_argument("--must-do", default="")
    parser.add_argument("--optional", default="")
    parser.add_argument("--out-dir", type=Path, default=Path.cwd())
    parser.add_argument("--until", choices=("draft", "validate", "review", "export"), default="export")
    parser.add_argument("--reviewer", default="native_subagent", choices=("native_subagent", "role_simulation", "human"))
    parser.add_argument("--force", action="store_true", help="docx 已存在时覆盖并保留 .bak")
    parser.add_argument("--strict-metadata", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict] = []
    if args.plan:
        plan_path = Path(args.plan)
        plan = load_json(plan_path)
        out_dir = plan_path.parent
    else:
        if not (args.week and args.session and args.title):
            raise CliError("MISSING_INPUT", "草稿模式需要 --week/--session/--title", "或使用 --plan 续跑")
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
        plan_path = out_dir / f"教案_{_safe(args.title)}_第{args.week}周第{args.session}次.json"
        plan_path.write_text(dump(plan) + "\n", encoding="utf-8", newline="\n")
    steps.append({"step": "draft", "ok": True, "path": str(plan_path)})
    if args.until == "draft":
        print(dump({"ok": True, "until": args.until, "steps": steps}))
        return 0

    check = validate_plan(plan)
    steps.append({"step": "validate", "ok": check["ok"], "issues": check["issues"]})
    if not check["ok"]:
        print(dump({"ok": False, "until": args.until, "steps": steps}))
        return 1
    if args.until == "validate":
        print(dump({"ok": True, "until": args.until, "steps": steps}))
        return 0

    report = adversarial_review(plan, no_counterexample=True, reviewer=args.reviewer)
    report_path = default_review_path(plan_path)
    save_review_report(report_path, report)
    steps.append({"step": "review", "ok": report.get("status") == "passed", "path": str(report_path), "status": report.get("status")})
    if report.get("status") != "passed":
        print(dump({"ok": False, "until": args.until, "steps": steps}))
        return 2
    if args.until == "review":
        print(dump({"ok": True, "until": args.until, "steps": steps}))
        return 0

    output = out_dir / f"教案_{_safe(str(plan.get('contentTitle') or '未命名课题'))}_第{plan.get('week')}周第{plan.get('session')}次.docx"
    if output.exists():
        if not args.force:
            raise CliError("OUTPUT_EXISTS", f"目标文件已存在：{output.name}", "确认覆盖时加 --force")
        shutil.copy2(output, output.with_name(output.name + ".bak"))
    export_docx(
        plan,
        output,
        base_dir=plan_path.parent,
        independence=report.get("independence") or report.get("reviewer"),
        overrides=report.get("overrides") if isinstance(report.get("overrides"), list) else None,
        strict_metadata=args.strict_metadata,
    )
    steps.append({"step": "export", "ok": True, "path": str(output), "bytes": output.stat().st_size})
    print(dump({"ok": True, "until": args.until, "steps": steps, "plan": str(plan_path), "docx": str(output), "review": str(report_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(run_cli(main))
