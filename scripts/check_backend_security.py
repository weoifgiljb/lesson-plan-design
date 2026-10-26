# -*- coding: utf-8 -*-
"""G3 后端安全闸门：上传、SQL、会话、口令、密钥、PII、日志与路径。

只读源码文本与 AST；不执行被检查代码。规则编号见 docs/backend-review-gate.md §5。
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gate_common as common  # noqa: E402

TEXT_SUFFIXES = {".py", ".sql", ".ts", ".vue", ".json"}
PII_RE = re.compile(r"student(Name|Id|No)?|学号|身份证|id_card", re.I)
SECRET_RE = re.compile(
    r"(?i)\b(secret|password|passwd|token|api[_-]?key)[A-Za-z0-9_]*\b\s*=\s*[\"'][^\"'\n]{6,}[\"']"
)
DEBUG_RE = re.compile(r"(?i)\bdebug\s*=\s*True\b")
LOG_RE = re.compile(r"(?i)(?:logger|logging)\.\w+\([^)\n]*\b(plan|report_json|password|token|cookie)\b")
SQL_TABLE_TRIGGER_RE = re.compile(
    r"CREATE\s+TRIGGER[^;]{0,600}?{table}[^;]{0,600}?BEFORE\s+{op}[^;]{0,600}?RAISE\s*\(\s*ABORT",
    re.I | re.S,
)
RETURNED_HASH_ALLOWED = re.compile(r"(?i)safe_join|normalize_entry|safe_extract")


def _trigger_re(table: str, op: str) -> re.Pattern[str]:
    pattern = SQL_TABLE_TRIGGER_RE.pattern.replace("{table}", re.escape(table)).replace("{op}", op)
    return re.compile(pattern, re.I | re.S)


def _files(root: Path) -> list[Path]:
    return [path for path in common.iter_py(root) if path.is_file()]


def _check_zip(files: list[Path], backend: Path) -> list[dict]:
    problems = []
    archive = backend / "app" / "adapters" / "archive.py"
    uses_zip = False
    for path in files:
        text = common.read_text(path)
        if "zipfile" in text:
            uses_zip = True
        if path != archive:
            tree = common.parse(path)
            if tree is not None:
                for ref in sorted(common.module_refs(tree)):
                    if ref == "zipfile" or ref.startswith("zipfile."):
                        problems.append(common.problem("BSEC-01", path, 0, "zipfile 只允许在 adapters/archive.py 使用"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and common.call_name(node).endswith((".extract", ".extractall")):
                        problems.append(common.problem("BSEC-01", path, node.lineno, "禁止 extract/extractall"))
    if uses_zip:
        text = common.read_text(archive)
        if not RETURNED_HASH_ALLOWED.search(text):
            problems.append(common.problem("BSEC-01", archive, 0, "archive.py 必须提供 safe_join/normalize_entry"))
    return problems


def _is_sql_splice(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return True
    if isinstance(node, ast.Call) and common.call_name(node).endswith(".format"):
        return True
    return False


def _check_sql(files: list[Path]) -> list[dict]:
    problems = []
    for path in files:
        tree = common.parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = common.call_name(node)
            if not name.endswith((".execute", ".executemany")):
                continue
            for arg in node.args:
                if _is_sql_splice(arg):
                    problems.append(common.problem("BSEC-02", path, node.lineno, "SQL 禁止用 f-string/%/format 拼接"))
    return problems


def _check_schema(backend: Path) -> list[dict]:
    schema = backend / "app" / "adapters" / "db" / "schema.sql"
    if not schema.is_file():
        return [common.problem("BSEC-03", schema, 0, "缺少 app/adapters/db/schema.sql")]
    text = common.read_text(schema)
    problems = []
    if not re.search(r"journal_mode\s*=\s*WAL", text, re.I):
        problems.append(common.problem("BSEC-03", schema, 0, "缺少 PRAGMA journal_mode=WAL"))
    if not re.search(r"foreign_keys\s*=\s*ON", text, re.I):
        problems.append(common.problem("BSEC-03", schema, 0, "缺少 PRAGMA foreign_keys=ON"))
    for table in ("plan_version", "audit_log", "sync_log"):
        for op in ("UPDATE", "DELETE"):
            if not _trigger_re(table, op).search(text):
                problems.append(
                    common.problem(
                        "BSEC-03", schema, 0, f"{table} 缺少 BEFORE {op} 的不可变触发器"
                    )
                )
    return problems


def _check_cookie(files: list[Path], backend: Path) -> list[dict]:
    problems = []
    deps = backend / "app" / "api" / "deps.py"
    for path in files:
        tree = common.parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not common.call_name(node).endswith(".set_cookie"):
                continue
            if path != deps:
                problems.append(common.problem("BSEC-04", path, node.lineno, "set_cookie 只允许在 api/deps.py"))
                continue
            keywords = {keyword.arg for keyword in node.keywords if keyword.arg}
            if "httponly" not in keywords or "samesite" not in keywords:
                problems.append(common.problem("BSEC-04", path, node.lineno, "Cookie 必须设置 httponly 与 samesite"))
    return problems


def _check_password(files: list[Path], backend: Path) -> list[dict]:
    problems = []
    for path in files:
        text = common.read_text(path)
        if re.search(r"hashlib\.(md5|sha1)\s*\(", text):
            problems.append(common.problem("BSEC-05", path, 0, "口令不得使用 md5/sha1"))
    security = backend / "app" / "domain" / "security.py"
    text = common.read_text(security)
    if not re.search(r"scrypt\s*\(|pbkdf2_hmac\s*\(", text):
        problems.append(common.problem("BSEC-05", security, 0, "domain/security.py 必须使用 scrypt 或 pbkdf2_hmac"))
    return problems


def _check_secrets(files: list[Path]) -> list[dict]:
    problems = []
    for path in files:
        if "tests" in path.parts:
            continue
        text = common.read_text(path)
        for number, line in enumerate(text.splitlines(), 1):
            if SECRET_RE.search(line):
                problems.append(common.problem("BSEC-06", path, number, "疑似硬编码密钥或口令"))
            if DEBUG_RE.search(line):
                problems.append(common.problem("BSEC-06", path, number, "禁止 debug=True"))
    return problems


def _check_pii(roots: list[Path]) -> list[dict]:
    problems = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            for number, line in enumerate(common.read_text(path).splitlines(), 1):
                if PII_RE.search(line):
                    problems.append(common.problem("BSEC-07", path, number, "不得出现学生个人信息字段"))
    return problems


def _check_logging(files: list[Path], backend: Path) -> list[dict]:
    problems = []
    for path in files:
        text = common.read_text(path)
        for number, line in enumerate(text.splitlines(), 1):
            if LOG_RE.search(line):
                problems.append(common.problem("BSEC-08", path, number, "日志不得记录教案全文、口令或令牌"))
    main_text = common.read_text(backend / "app" / "main.py")
    lowered = main_text.lower()
    if "trace" not in lowered or "middleware" not in lowered:
        problems.append(common.problem("BSEC-08", backend / "app" / "main.py", 0, "main.py 必须提供 traceId 中间件"))
    return problems


def _check_limits(files: list[Path], backend: Path) -> list[dict]:
    config = backend / "app" / "config.py"
    config_text = common.read_text(config)
    if "MAX_PACKAGE_BYTES" not in config_text:
        return [common.problem("BSEC-09", config, 0, "config.py 必须定义 MAX_PACKAGE_BYTES")]
    used = any(
        "MAX_PACKAGE_BYTES" in common.read_text(path) for path in files if path != config
    )
    if not used:
        return [common.problem("BSEC-09", config, 0, "MAX_PACKAGE_BYTES 未被上传路径使用")]
    return []


def _check_storage(backend: Path) -> list[dict]:
    storage = backend / "app" / "adapters" / "storage.py"
    text = common.read_text(storage)
    problems = []
    if ".resolve(" not in text:
        problems.append(common.problem("BSEC-10", storage, 0, "storage.py 必须调用 resolve() 规范化路径"))
    if "is_relative_to(" not in text:
        problems.append(common.problem("BSEC-10", storage, 0, "storage.py 必须用 is_relative_to 校验落盘位置"))
    return problems


def scan(backend=None, frontend=None) -> list[dict]:
    backend = backend or common.BACKEND
    frontend = frontend or common.FRONTEND
    if not backend.is_dir():
        return []
    files = _files(backend / "app")
    problems: list[dict] = []
    problems += _check_zip(files, backend)
    problems += _check_sql(files)
    problems += _check_schema(backend)
    problems += _check_cookie(files, backend)
    problems += _check_password(files, backend)
    problems += _check_secrets(files)
    problems += _check_pii([backend, frontend])
    problems += _check_logging(files, backend)
    problems += _check_limits(files, backend)
    problems += _check_storage(backend)
    return problems


def main() -> int:
    args = common.parser("G3 后端安全闸门").parse_args()
    if common.backend_absent():
        return common.emit("security", [], skipped=True, as_json=args.json)
    return common.emit("security", scan(), as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
