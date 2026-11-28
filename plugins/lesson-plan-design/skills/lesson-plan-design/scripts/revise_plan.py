# -*- coding: utf-8 -*-
"""按字段路径修订教案 JSON，并显式提示旧审查报告失效。"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import CliError, JsonArgumentParser, run_cli
from lib import default_review_path, dump, load_json, load_review_report, plan_hash, validate_plan


def _parse_path(path: str) -> list[str | int]:
    parts: list[str | int] = []
    for token in str(path).split("."):
        while "[" in token:
            head, _, rest = token.partition("[")
            if head:
                parts.append(head)
            index, _, tail = rest.partition("]")
            if not index.isdigit():
                raise CliError("INVALID_PATH", f"字段路径非法：{path}", "列表下标必须是数字，例如 activityFlow.taskImplementation[0]")
            parts.append(int(index))
            token = tail
        if token:
            parts.append(token)
    if not parts:
        raise CliError("INVALID_PATH", "字段路径不能为空", "例如 title 或 activityFlow.assessment")
    return parts


def _get(plan: dict, parts: list[str | int], raw: str) -> object:
    current: object = plan
    for part in parts:
        if isinstance(part, int):
            if not isinstance(current, list) or part >= len(current):
                raise CliError("INVALID_PATH", f"字段路径不存在：{raw}", "先用 validate.py --examples 对照结构")
            current = current[part]
        else:
            if not isinstance(current, dict) or part not in current:
                raise CliError("INVALID_PATH", f"字段路径不存在：{raw}", "只允许修改教案已有字段")
            current = current[part]
    return current


def _set(plan: dict, parts: list[str | int], value: object, raw: str) -> None:
    current: object = plan
    for part in parts[:-1]:
        if isinstance(part, int):
            if not isinstance(current, list) or part >= len(current):
                raise CliError("INVALID_PATH", f"字段路径不存在：{raw}", "列表下标越界")
            current = current[part]
        else:
            if not isinstance(current, dict) or part not in current:
                raise CliError("INVALID_PATH", f"字段路径不存在：{raw}", "只允许修改教案已有字段")
            current = current[part]
    last = parts[-1]
    if isinstance(last, int):
        if not isinstance(current, list) or last >= len(current):
            raise CliError("INVALID_PATH", f"字段路径不存在：{raw}", "列表下标越界")
        current[last] = value
    else:
        if not isinstance(current, dict) or last not in current:
            raise CliError("INVALID_PATH", f"字段路径不存在：{raw}", "只允许修改教案已有字段")
        current[last] = value


def _value(raw: str) -> object:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def main() -> int:
    parser = JsonArgumentParser(description="按字段路径修订教案 JSON")
    parser.add_argument("path", help="教案 JSON")
    parser.add_argument("--set", action="append", default=[], metavar="PATH=VALUE", help="可重复，例如 title=新课题")
    parser.add_argument("--dry-run", action="store_true", help="只输出变更，不写文件")
    args = parser.parse_args()
    plan_path = Path(args.path)
    if not args.set:
        raise CliError("INVALID_PATH", "至少提供一个 --set PATH=VALUE", "例如 --set title=新课题")
    original = load_json(plan_path)
    revised = copy.deepcopy(original)
    changes = []
    for assignment in args.set:
        if "=" not in assignment:
            raise CliError("INVALID_PATH", f"--set 需要 PATH=VALUE：{assignment}", "等号左侧是字段路径")
        raw_path, raw_value = assignment.split("=", 1)
        parts = _parse_path(raw_path.strip())
        before = _get(revised, parts, raw_path.strip())
        value = _value(raw_value)
        _set(revised, parts, value, raw_path.strip())
        changes.append({"path": raw_path.strip(), "before": before, "after": value})
    check = validate_plan(revised)
    if not check["ok"]:
        raise CliError("VALIDATION_FAILED", "修订后教案未通过结构校验", "；".join(check["issues"]))
    old_hash = plan_hash(original)
    new_hash = plan_hash(revised)
    review_invalidated = False
    report_path = default_review_path(plan_path)
    if report_path.is_file():
        try:
            report = load_review_report(report_path)
            review_invalidated = str(report.get("planHash") or "") != new_hash
        except (OSError, ValueError, json.JSONDecodeError):
            review_invalidated = True
    if not args.dry_run:
        temporary = plan_path.with_name(plan_path.name + ".tmp")
        try:
            temporary.write_text(dump(revised) + "\n", encoding="utf-8", newline="\n")
            temporary.replace(plan_path)
        finally:
            if temporary.exists():
                temporary.unlink()
    print(dump({
        "ok": True,
        "path": str(plan_path),
        "dryRun": args.dry_run,
        "changes": changes,
        "oldPlanHash": old_hash,
        "newPlanHash": new_hash,
        "reviewInvalidated": review_invalidated,
        "warnings": ["旧审查报告已失效，请重新运行 adversarial_review.py"] if review_invalidated else [],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(run_cli(main))
