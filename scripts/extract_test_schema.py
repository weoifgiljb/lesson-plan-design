# -*- coding: utf-8 -*-
"""从 测试用例_markmap.md 抽取 测试用例.schema.yaml。

按 .dsh/skills/core/schema-extraction.md 的三层形态输出：meta / modules / cases。
不依赖 PyYAML；字符串统一用 JSON 双引号形式（合法 YAML 标量）。
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASE_RE = re.compile(r"^- \*\*(TC-(\d{2})-(\d{2})) (.+?)\*\* \[(P[012])\](?:（SMOKE-(\d+)）)?(.*)$")
MODULE_RE = re.compile(r"^## (\d+)\. (.+)$")
SHARED_RE = re.compile(r"^> 前置[:：]\s*(.+)$")
TAG_RE = re.compile(r"\[(安全|并发|可靠|兼容|迁移|集成|国际化|需Mock|需真机|需专业环境)\]")
CODE_ROW_RE = re.compile(r"^\|\s*(TC-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|$")

MODULE_TYPES = {
    "1": "data",
    "2": "boundary",
    "3": "state",
    "4": "exception",
    "5": "data",
    "6": "functional",
    "7": "state",
    "8": "concurrency",
    "9": "permission",
    "10": "functional",
    "11": "functional",
    "12": "functional",
}
PLUGIN_MODULES = {"2", "3", "4", "5"}
PLUGIN_EVIDENCE = {
    "level": "E2",
    "source": "插件端源码与本地实测（commit ecbdf49）",
    "confidence": "high",
}
PLATFORM_EVIDENCE = {
    "level": "E1",
    "source": "平台端需求文档（功能优化需求-BS平台端 v1.0，尚未实现）",
    "confidence": "medium",
}
NO_CODE = "平台端未实现，无代码位置"


def q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse(markdown_path: Path) -> tuple[list[dict], list[dict], dict[str, list[str]]]:
    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    code_refs: dict[str, list[str]] = {}
    for line in lines:
        match = CODE_ROW_RE.match(line.strip())
        if match:
            refs = [part.strip() for part in re.split(r"[、,，]", match.group(2)) if part.strip()]
            code_refs[match.group(1)] = refs

    modules: list[dict] = []
    cases: list[dict] = []
    module_no = ""
    module_title = ""
    shared: list[str] = []
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            cases.append(current)
            current = None

    for raw in lines:
        line = raw.rstrip()
        module_match = MODULE_RE.match(line)
        if module_match:
            flush()
            module_no = module_match.group(1)
            module_title = f"{module_no}. {module_match.group(2).strip()}"
            shared = []
            modules.append({"module": module_title, "shared_preconditions": shared})
            continue
        if line.startswith("## "):
            flush()
            module_no = ""
            continue
        if module_no and SHARED_RE.match(line.strip()):
            shared.append(SHARED_RE.match(line.strip()).group(1).strip())
            continue
        case_match = CASE_RE.match(line)
        if case_match:
            flush()
            tc_id, tc_module, _seq, title, priority, smoke, rest = case_match.groups()
            tags = TAG_RE.findall(title + " " + rest)
            clean_title = TAG_RE.sub("", title).strip()
            clean_title = re.sub(r"\s{2,}", " ", clean_title)
            current = {
                "id": tc_id,
                "title": clean_title,
                "module_no": tc_module,
                "module": module_title,
                "priority": priority,
                "smoke": f"SMOKE-{smoke}" if smoke else "",
                "tags": tags,
                "preconditions": [],
                "steps": [],
                "expected": [],
            }
            continue
        if current is not None and line.startswith("  - "):
            content = line[4:].strip()
            if ":" in content:
                key, value = content.split(":", 1)
            elif "：" in content:
                key, value = content.split("：", 1)
            else:
                continue
            key = key.strip()
            value = value.strip()
            if key.startswith("前置条件"):
                current["preconditions"].append(value)
            elif key.startswith("操作步骤"):
                current["steps"].append(value)
            elif key.startswith("预期结果"):
                current["expected"].append(value)
            elif key.startswith("验证方式"):
                current["expected"].append(f"验证方式：{value}")
    flush()
    return modules, cases, code_refs


def build_cases(cases: list[dict], code_refs: dict[str, list[str]]) -> list[dict]:
    result = []
    for case in cases:
        module_no = str(int(case["module_no"]))
        plugin = module_no in PLUGIN_MODULES
        refs = code_refs.get(case["id"]) or [NO_CODE]
        tags = list(case["tags"])
        case_type = MODULE_TYPES.get(module_no, "functional")
        if "安全" in tags:
            case_type = "security"
        if "并发" in tags:
            case_type = "concurrency"
        result.append(
            {
                "id": case["id"],
                "title": case["title"],
                "module": case["module"],
                "priority": case["priority"],
                "type": case_type,
                "execution_model": "dev-collab" if plugin else "ui",
                "smoke": case["smoke"],
                "preconditions": case["preconditions"],
                "steps": case["steps"],
                "expected": case["expected"],
                "test_data": {},
                "code_refs": refs,
                "evidence": dict(PLUGIN_EVIDENCE if plugin else PLATFORM_EVIDENCE),
                "tags": tags,
                "automation": {
                    "supported": "partial" if plugin else "no",
                    "framework": "api" if plugin else "manual",
                },
                "status": "active",
            }
        )
    return result


def emit(modules: list[dict], cases: list[dict], source: str) -> str:
    out: list[str] = []
    out.append("meta:")
    out.append(f"  source_markmap: {q(source)}")
    out.append(f"  extracted_at: {q(date.today().isoformat())}")
    out.append("modules:")
    for module in modules:
        out.append(f"  - module: {q(module['module'])}")
        if module["shared_preconditions"]:
            out.append("    shared_preconditions:")
            for item in module["shared_preconditions"]:
                out.append(f"      - {q(item)}")
        else:
            out.append("    shared_preconditions: []")
    out.append("cases:")
    for case in cases:
        out.append(f"  - id: {q(case['id'])}")
        out.append(f"    title: {q(case['title'])}")
        out.append(f"    module: {q(case['module'])}")
        out.append(f"    priority: {q(case['priority'])}")
        out.append(f"    type: {q(case['type'])}")
        out.append(f"    execution_model: {q(case['execution_model'])}")
        if case["smoke"]:
            out.append(f"    smoke: {q(case['smoke'])}")
        for field in ("preconditions", "steps", "expected", "code_refs", "tags"):
            values = case[field]
            if values:
                out.append(f"    {field}:")
                for value in values:
                    out.append(f"      - {q(value)}")
            else:
                out.append(f"    {field}: []")
        out.append("    test_data: {}")
        out.append("    evidence:")
        out.append(f"      level: {q(case['evidence']['level'])}")
        out.append(f"      source: {q(case['evidence']['source'])}")
        out.append(f"      confidence: {q(case['evidence']['confidence'])}")
        out.append("    automation:")
        out.append(f"      supported: {q(case['automation']['supported'])}")
        out.append(f"      framework: {q(case['automation']['framework'])}")
        out.append("    status: \"active\"")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="抽取测试用例 schema")
    parser.add_argument("--markmap", default=str(ROOT / "测试用例_markmap.md"))
    parser.add_argument("--out", default=str(ROOT / "测试用例.schema.yaml"))
    args = parser.parse_args()
    source = Path(args.markmap)
    modules, raw_cases, refs = parse(source)
    cases = build_cases(raw_cases, refs)
    Path(args.out).write_text(emit(modules, cases, source.name), encoding="utf-8")
    print(f"cases={len(cases)} modules={len(modules)} -> {args.out}")
    problems: list[str] = []
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        problems.append("用例编号重复")
    for case in cases:
        if not case["steps"] or not case["expected"]:
            problems.append(f"{case['id']} 缺少步骤或预期")
        if not case["code_refs"]:
            problems.append(f"{case['id']} 缺少代码位置")
        module_no = str(int(case["id"].split("-")[1]))
        if not case["module"].startswith(module_no + "."):
            problems.append(f"{case['id']} 模块号不一致")
    distribution: dict[str, int] = {}
    for case in cases:
        distribution[case["priority"]] = distribution.get(case["priority"], 0) + 1
    print("priority", distribution)
    if problems:
        for problem in problems:
            print("ERROR", problem)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
