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
CATALOG_NAME = "CATALOG.md"


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
            "contentDetail": plan.get("contentDetail", ""),
            "academicYear": plan.get("academicYear", ""),
            "semester": plan.get("semester"),
            "planHash": plan_hash(plan),
            "version": VERSION,
        })
    return {"schemaVersion": 1, "count": len(examples), "examples": examples}


def render_catalog(index: dict) -> str:
    lines = [
        "# 样例目录",
        "",
        "金标准 JSON 在 `examples/`。按课程、周次与课次选用最接近的一份，只 Read 需要的文件。",
        "",
        "| 文件 | 课程 | 周次 | 课次 | 课题 | 内容/套别 |",
        "|---|---|---|---|---|---|",
    ]
    for item in index.get("examples", []):
        lines.append(
            "| `examples/{file}` | {course} | {week} | {session} | {title} | {detail} |".format(
                file=item.get("file", ""),
                course=item.get("course", ""),
                week=item.get("week", ""),
                session=item.get("session", ""),
                title=item.get("contentTitle", ""),
                detail=str(item.get("contentDetail", "")).replace("|", "\\|"),
            )
        )
    lines.extend(
        [
            "",
            "字段说明见 `references/schema.md`。校验规则见 `references/validation.md`。空骨架见 `templates/empty-plan.json`。",
            "",
        ]
    )
    return "\n".join(lines)


def check_catalog(directory: Path, catalog: Path | None = None) -> list[str]:
    path = Path(catalog) if catalog is not None else directory.parent / CATALOG_NAME
    expected = render_catalog(build_index(directory))
    if not path.is_file():
        return [f"缺少目录：{path}"]
    if path.read_text(encoding="utf-8") != expected:
        return [f"目录内容过期：{path}（重新运行 --write）"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="生成或校验 examples/index.json 与 CATALOG.md")
    parser.add_argument("--examples-dir", default=str(EXAMPLES_DIR), help="样例目录")
    parser.add_argument("--catalog", type=Path, default=None, help="CATALOG.md 路径；默认样例目录上层")
    parser.add_argument("--check", action="store_true", help="校验 index.json 与 CATALOG.md（默认）")
    parser.add_argument("--write", action="store_true", help="重新生成 index.json 与 CATALOG.md")
    args = parser.parse_args()
    directory = Path(args.examples_dir)
    catalog_path = args.catalog or directory.parent / CATALOG_NAME
    if not directory.is_dir():
        print(dump({"ok": False, "errors": [f"样例目录不存在：{directory}"]}), file=sys.stderr)
        return 1
    if args.write:
        index = build_index(directory)
        index_path = directory / "index.json"
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        catalog_path = Path(args.catalog) if args.catalog else directory.parent / CATALOG_NAME
        catalog_path.write_text(render_catalog(index), encoding="utf-8", newline="\n")
        result = check_examples(directory)
        result["catalog"] = check_catalog(directory, catalog_path)
        result["ok"] = result["ok"] and not result["catalog"]
        result["written"] = str(index_path)
        result["catalogPath"] = str(catalog_path)
        print(dump(result))
        return 0 if result["ok"] else 1
    result = check_examples(directory)
    result["catalog"] = check_catalog(directory, catalog_path)
    result["ok"] = result["ok"] and not result["catalog"]
    print(dump(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
