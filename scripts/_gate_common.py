# -*- coding: utf-8 -*-
"""后端闸门共用工具：路径、AST、行数与统一 JSON 输出。

所有 check_backend_*.py 只读源码；这里不做业务判断，只提供可复用能力。
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# LPP_BACKEND_ROOT 供测试与临时验证覆盖"后端是否存在"，默认取仓库内路径。
BACKEND = Path(os.environ.get("LPP_BACKEND_ROOT", str(ROOT / "src" / "backend")))
FRONTEND = Path(os.environ.get("LPP_FRONTEND_ROOT", str(ROOT / "src" / "frontend")))
APP = BACKEND / "app"
CONTRACT = ROOT / "docs" / "api" / "contract.v1.json"
OPENAPI = ROOT / "docs" / "api" / "openapi.v1.json"
PLUGIN_SCRIPTS = ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "scripts"
PLUGIN_MODEL = PLUGIN_SCRIPTS / "lesson_plan" / "model.py"
PLUGIN_FOOTER = PLUGIN_SCRIPTS / "docx_export" / "footer.py"

LAYERS = ("domain", "application", "adapters", "api")
SEVERITY_BLOCK = "block"
SEVERITY_WARN = "warn"
ABSOLUTE_PATH_RE = re.compile(r"(?i)\b[A-Z]:[\\/]Users[\\/]|/home/[^/\s]+/")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def iter_py(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.rglob("*.py") if path.is_file())


def parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def module_refs(tree: ast.Module) -> set[str]:
    """返回本次 import 涉及的模块全名（from a.b import c 记 a.b）。"""
    refs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                refs.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            refs.add(node.module)
            for alias in node.names:
                refs.add(f"{node.module}.{alias.name}")
    return refs


def matches(ref: str, forbidden: set[str]) -> bool:
    """ref 等于某禁用项，或位于其包路径下。"""
    parts = ref.split(".")
    for index in range(1, len(parts) + 1):
        if ".".join(parts[:index]) in forbidden:
            return True
    return False


def import_problems(path: Path, tree: ast.Module, forbidden: set[str], rule: str) -> list[dict]:
    problems = []
    for ref in sorted(module_refs(tree)):
        if matches(ref, forbidden):
            problems.append(problem(rule, path, 0, f"禁止 import {ref}"))
    return problems


def problem(rule: str, path: Path | str, line: int, detail: str, severity: str = SEVERITY_BLOCK) -> dict:
    return {
        "rule": rule,
        "file": path if isinstance(path, str) else rel(path),
        "line": line,
        "detail": detail,
        "severity": severity,
    }


def line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeDecodeError):
        return 0


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        base = call_name_of_expr(node.func.value)
        return f"{base}.{node.func.attr}" if base else node.func.attr
    return ""


def call_name_of_expr(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = call_name_of_expr(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def max_nesting(node: ast.AST, depth: int = 0) -> int:
    blocks = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)
    if isinstance(node, blocks):
        depth += 1
    deepest = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and depth == 0:
            continue
        deepest = max(deepest, max_nesting(child, depth))
    return deepest


def function_stats(tree: ast.Module) -> list[tuple[str, int, int, int]]:
    """返回 [(函数名, 起始行, 长度, 最大嵌套)]。"""
    stats = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            stats.append((node.name, node.lineno, length, max_nesting(node, 1)))
    return stats


def emit(gate: str, problems: list[dict], *, skipped: bool = False, as_json: bool = False) -> int:
    blocks = [item for item in problems if item.get("severity") != SEVERITY_WARN]
    warns = [item for item in problems if item.get("severity") == SEVERITY_WARN]
    payload = {
        "gate": gate,
        "ok": not blocks,
        "skipped": skipped,
        "blocks": blocks,
        "warns": warns,
        "count": len(problems),
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif skipped:
        print(f"SKIP  {gate}（未发现 src/backend，后端尚未开工）")
    else:
        for item in blocks + warns:
            print(f"{item['severity'].upper():<5} {item['rule']}  {item['file']}:{item['line']}  {item['detail']}")
        print(f"{'OK' if payload['ok'] else 'FAIL'}  {gate}：block {len(blocks)}，warn {len(warns)}")
    return 0 if payload["ok"] else 1


def parser(description: str) -> argparse.ArgumentParser:
    item = argparse.ArgumentParser(description=description)
    item.add_argument("--json", action="store_true", help="JSON 输出")
    return item


def backend_absent() -> bool:
    return not BACKEND.is_dir()


def load_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def constant_strings(tree: ast.Module, name: str) -> set[str]:
    """读取模块级 name = {...}/[...]/(...) 里的字符串常量，兼容 dict 键与集合。"""
    values: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [item.id for item in node.targets if isinstance(item, ast.Name)]
        if name not in targets:
            continue
        values |= _strings_of(node.value)
    return values


def _strings_of(node: ast.AST) -> set[str]:
    values: set[str] = set()
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        values.add(node.value)
    elif isinstance(node, ast.Dict):
        for key in node.keys:
            if key is not None:
                values |= _strings_of(key)
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for item in node.elts:
            values |= _strings_of(item)
    elif isinstance(node, ast.Call):
        for arg in node.args:
            values |= _strings_of(arg)
        for keyword in node.keywords:
            values |= _strings_of(keyword.value)
    return values


def walk_calls(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node
