# -*- coding: utf-8 -*-
"""G1 后端架构闸门：分层、体量、错误边界与单一接入点。

只用 AST 与源码文本，不 import 被检查代码；每次调用 ``scan()`` 返回问题列表。
规则编号见 docs/backend/backend-review-gate.md §3。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gate_common as common  # noqa: E402

FORBIDDEN_DOMAIN = {
    "fastapi",
    "starlette",
    "uvicorn",
    "sqlite3",
    "requests",
    "httpx",
    "subprocess",
    "app.api",
    "app.adapters",
    "app.application",
}
FORBIDDEN_APPLICATION = {"fastapi", "starlette", "uvicorn", "app.api"}
FORBIDDEN_ADAPTERS = {"app.api", "app.application"}
FORBIDDEN_API = {"sqlite3", "zipfile", "subprocess", "app.adapters.db"}
EXCEPT_WHITELIST = {"api/errors.py", "main.py", "adapters/archive.py", "adapters/db/repo.py", "adapters/engine.py", "adapters/storage.py"}
MODULE_LIMITS = {"domain": 300, "application": 300, "api_routers": 200, "main": 150}
BLOCK_RATIO = 1.2
TEXT_SUFFIXES = {".py", ".ts", ".vue", ".json", ".sql", ".md", ".ps1"}


def _layer_of(path, app):
    try:
        return path.relative_to(app).as_posix()
    except ValueError:
        return path.name


def _module_limit(relative: str) -> int | None:
    if relative == "main.py":
        return MODULE_LIMITS["main"]
    if relative.startswith("domain/"):
        return MODULE_LIMITS["domain"]
    if relative.startswith("application/"):
        return MODULE_LIMITS["application"]
    if relative.startswith("api/routers/"):
        return MODULE_LIMITS["api_routers"]
    return None


def _check_imports(files, forbidden, rule, app):
    problems = []
    for path in files:
        tree = common.parse(path)
        if tree is None:
            problems.append(common.problem(rule, path, 0, "无法解析为 Python"))
            continue
        problems.extend(common.import_problems(path, tree, forbidden, rule))
    return problems


def _check_domain_calls(files):
    problems = []
    for path in files:
        tree = common.parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and common.call_name_of_expr(node) == "os.environ":
                problems.append(common.problem("BA-03", path, node.lineno, "domain 不得读取 os.environ"))
                continue
            if not isinstance(node, ast.Call):
                continue
            name = common.call_name(node)
            if name in {"print", "open"} or name.endswith((".write_text", ".write_bytes")):
                problems.append(common.problem("BA-03", path, node.lineno, f"domain 不得调用 {name}"))
            elif name in {"sys.exit"} or name.startswith("os.environ."):
                problems.append(common.problem("BA-03", path, node.lineno, f"domain 不得调用 {name}"))
    return problems


def _check_size(files, app):
    problems = []
    for path in files:
        relative = _layer_of(path, app)
        limit = _module_limit(relative)
        if limit is not None:
            count = common.line_count(path)
            if count > limit * BLOCK_RATIO:
                problems.append(
                    common.problem("BA-07", path, 1, f"模块 {count} 行，超过 {limit} 行上限的 1.2 倍")
                )
            elif count > limit:
                problems.append(
                    common.problem("BA-07", path, 1, f"模块 {count} 行，超过建议上限 {limit}", common.SEVERITY_WARN)
                )
        tree = common.parse(path)
        if tree is None:
            continue
        for name, line, length, nesting in common.function_stats(tree):
            if length > 75:
                problems.append(common.problem("BA-08", path, line, f"函数 {name} {length} 行，超过 50 行上限的 1.5 倍"))
            elif length > 50:
                problems.append(
                    common.problem("BA-08", path, line, f"函数 {name} {length} 行，超过建议 50 行", common.SEVERITY_WARN)
                )
            if nesting > 3:
                problems.append(
                    common.problem("BA-08", path, line, f"函数 {name} 嵌套 {nesting} 层", common.SEVERITY_WARN)
                )
    return problems


def _check_error_boundary(files, app):
    problems = []
    for path in files:
        relative = _layer_of(path, app)
        tree = common.parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if node.type is None:
                problems.append(common.problem("BA-09", path, node.lineno, "禁止裸 except"))
                continue
            if relative not in EXCEPT_WHITELIST:
                problems.append(
                    common.problem("BA-09", path, node.lineno, f"except 只允许出现在 {sorted(EXCEPT_WHITELIST)}")
                )
    return problems


def _check_error_codes(files, app, errors_file):
    problems = []
    tree = common.parse(errors_file)
    codes = common.constant_strings(tree, "ERROR_CODES") if tree is not None else set()
    if not codes:
        problems.append(common.problem("BA-10", errors_file, 0, "domain/errors.py 必须定义 ERROR_CODES 常量表"))
        return problems
    for path in files:
        if path == errors_file:
            continue
        tree = common.parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = common.call_name(node)
            if not (name == "AppError" or name.endswith(".AppError")):
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            code = node.args[0].value
            if isinstance(code, str) and code not in codes:
                problems.append(
                    common.problem("BA-10", path, node.lineno, f"错误码 {code} 未登记在 ERROR_CODES")
                )
    return problems


def _check_engine_entry(files, app):
    problems = []
    engine = app / "adapters" / "engine.py"
    for path in files:
        tree = common.parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            name = common.call_name_of_expr(node) if isinstance(node, ast.Attribute) else ""
            if name == "sys.path":
                if path != engine:
                    problems.append(common.problem("BA-11", path, node.lineno, "sys.path 只允许在 adapters/engine.py 修改"))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "plugins/lesson-plan-design/skills" in node.value.replace("\\", "/") and path != engine:
                    problems.append(
                        common.problem("BA-11", path, node.lineno, "插件脚本路径只允许出现在 adapters/engine.py")
                    )
    return problems


def _check_absolute_paths(paths):
    problems = []
    for path in paths:
        text = common.read_text(path)
        for number, line in enumerate(text.splitlines(), 1):
            if common.ABSOLUTE_PATH_RE.search(line):
                problems.append(common.problem("BA-12", path, number, "不得写入本机绝对路径"))
    return problems


def scan(backend=None, frontend=None) -> list[dict]:
    root = backend or common.BACKEND
    if not root.is_dir():
        return []
    app = root / "app"
    problems: list[dict] = []

    # BA-01 目录与入口
    for name in ("main.py", "config.py"):
        if not (app / name).is_file():
            problems.append(common.problem("BA-01", app / name, 0, f"缺少 app/{name}"))
    for layer in common.LAYERS:
        if not (app / layer).is_dir():
            problems.append(common.problem("BA-01", app / layer, 0, f"缺少 app/{layer}/"))

    domain_files = common.iter_py(app / "domain")
    application_files = common.iter_py(app / "application")
    adapter_files = common.iter_py(app / "adapters")
    api_files = common.iter_py(app / "api")
    all_files = domain_files + application_files + adapter_files + api_files + [app / "main.py", app / "config.py"]
    all_files = [path for path in all_files if path.is_file()]

    problems += _check_imports(domain_files, FORBIDDEN_DOMAIN, "BA-02", app)
    problems += _check_domain_calls(domain_files)
    problems += _check_imports(api_files, FORBIDDEN_API, "BA-04", app)
    problems += _check_imports(application_files, FORBIDDEN_APPLICATION, "BA-05", app)
    problems += _check_imports(adapter_files, FORBIDDEN_ADAPTERS, "BA-06", app)
    problems += _check_size(all_files, app)
    problems += _check_error_boundary(all_files, app)
    problems += _check_error_codes(all_files, app, app / "domain" / "errors.py")
    problems += _check_engine_entry(all_files, app)

    text_paths = []
    for base in (root, frontend or common.FRONTEND):
        if base.is_dir():
            text_paths += [path for path in base.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES]
    problems += _check_absolute_paths(text_paths)
    return problems


def main() -> int:
    args = common.parser("G1 后端架构闸门").parse_args()
    if common.backend_absent():
        return common.emit("architecture", [], skipped=True, as_json=args.json)
    return common.emit("architecture", scan(), as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
