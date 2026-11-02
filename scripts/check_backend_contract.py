# -*- coding: utf-8 -*-
"""G2 契约闸门：contract ⇔ OpenAPI 快照 ⇔ 前端调用 ⇔ 错误码 ⇔ 版本白名单。

不 import 后端应用；`--update-contract` 才需要 FastAPI 环境生成快照。
规则编号见 docs/backend/backend-review-gate.md §4。
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gate_common as common  # noqa: E402

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PUBLIC_WRITE = {"/api/v1/auth/login"}
VALID_ROLES = {"teacher", "lead", "admin"}
CALL_RE = re.compile(r"client\.(get|post|put|patch|delete)\s*(?:<[^>]*>)?\s*\(\s*[`'\"]([^`'\"]+)[`'\"]", re.I)
QUOTED_CODE_RE = re.compile(r"[\"']([A-Z][A-Z0-9_]{3,})[\"']")
BARE_CODE_RE = re.compile(r"[{,]\s*([A-Z][A-Z0-9_]{3,})\s*:")
VERSION_LITERAL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\"[^\"]*\"|\d+(?:\.\d+)*)\s*$", re.M)


def _normalize_path(path: str) -> str:
    path = path.split("?")[0].strip()
    path = re.sub(r"\$\{[^}]+\}", "{id}", path)
    path = re.sub(r":[A-Za-z_][A-Za-z0-9_]*", "{id}", path)
    path = re.sub(r"\{[^}]+\}", "{id}", path)
    return path.rstrip("/") or "/"


def _contract_endpoints(contract: dict) -> list[dict]:
    items = contract.get("endpoints")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _check_contract_shape(contract: dict | None, path: Path) -> list[dict]:
    if contract is None:
        return [common.problem("BC-01", path, 0, "契约文件缺失或不是合法 JSON 对象")]
    problems = []
    for key in ("contractVersion", "versions", "roles", "errorCodes", "endpoints"):
        if key not in contract:
            problems.append(common.problem("BC-01", path, 0, f"契约缺少字段 {key}"))
    endpoints = _contract_endpoints(contract)
    if not endpoints:
        problems.append(common.problem("BC-01", path, 0, "契约 endpoints 为空"))
    for index, item in enumerate(endpoints, 1):
        for key in ("method", "path", "auth", "roles", "csrf", "idempotent", "status", "client"):
            if key not in item:
                problems.append(common.problem("BC-01", path, 0, f"第 {index} 个接口缺少字段 {key}"))
    return problems


def _check_roles(contract: dict, path: Path) -> list[dict]:
    problems = []
    declared = set(contract.get("roles") or [])
    for role in sorted(declared - VALID_ROLES):
        problems.append(common.problem("BC-04", path, 0, f"未登记角色 {role}"))
    for item in _contract_endpoints(contract):
        if item.get("auth") is False:
            continue
        roles = item.get("roles") or []
        if not roles:
            problems.append(common.problem("BC-04", path, 0, f"{item.get('method')} {item.get('path')} 未声明角色"))
        for role in sorted(set(roles) - VALID_ROLES):
            problems.append(
                common.problem("BC-04", path, 0, f"{item.get('method')} {item.get('path')} 角色 {role} 非法")
            )
    return problems


def _check_csrf(contract: dict, path: Path) -> list[dict]:
    problems = []
    for item in _contract_endpoints(contract):
        method = str(item.get("method", "")).upper()
        if method not in WRITE_METHODS or item.get("auth") is False:
            continue
        if item.get("path") in PUBLIC_WRITE:
            continue
        if item.get("csrf") is not True:
            problems.append(
                common.problem("BC-03", path, 0, f"{method} {item.get('path')} 必须声明 csrf=true")
            )
    return problems


def _openapi_routes(snapshot: dict) -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for path, methods in (snapshot.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        normalized = _normalize_path(path)
        for method in methods:
            routes.add((method.upper(), normalized))
    return routes


def _check_openapi(contract: dict, openapi_path: Path) -> list[dict]:
    """契约 ⇔ 代码路由。

    `implemented=false` 的接口允许暂缺（只报 warn）；标记 true 却缺、代码有但没翻转、
    以及未登记的路由，一律 block，避免"悄悄实现"或"忘记收尾"。
    """
    problems = []
    snapshot = common.load_json(openapi_path)
    if snapshot is None:
        return [common.problem("BC-02", openapi_path, 0, "缺少 OpenAPI 快照，运行 --update-contract 生成")]
    actual = _openapi_routes(snapshot)
    entries = {
        (str(item.get("method")).upper(), _normalize_path(str(item.get("path")))): item
        for item in _contract_endpoints(contract)
    }
    implemented = {key for key, item in entries.items() if item.get("implemented", True)}
    planned = set(entries) - implemented

    for method, path in sorted(implemented - actual):
        problems.append(common.problem("BC-02", openapi_path, 0, f"契约标记已实现的 {method} {path} 未在代码中出现"))
    for method, path in sorted(actual - set(entries)):
        problems.append(common.problem("BC-02", openapi_path, 0, f"代码实现的 {method} {path} 未登记在契约"))
    for method, path in sorted(actual & planned):
        problems.append(
            common.problem("BC-02", openapi_path, 0, f"{method} {path} 已实现，但契约 implemented=false，请同批翻转")
        )
    missing_planned = planned - actual
    if missing_planned:
        sample = "、".join(f"{method} {path}" for method, path in sorted(missing_planned)[:5])
        problems.append(
            common.problem(
                "BC-02",
                openapi_path,
                0,
                f"{len(missing_planned)} 个契约接口尚未实现（计划内）：{sample} 等",
                common.SEVERITY_WARN,
            )
        )
    return problems


def _domain_error_codes(errors_file: Path) -> set[str] | None:
    for candidate in (errors_file, errors_file.parent / "error_codes.py"):
        tree = common.parse(candidate)
        if tree is None:
            continue
        codes = common.constant_strings(tree, "ERROR_CODES")
        if codes:
            return codes
    return None


def _frontend_error_codes(errors_ts: Path) -> set[str] | None:
    text = common.read_text(errors_ts)
    if not text:
        return None
    return set(QUOTED_CODE_RE.findall(text)) | set(BARE_CODE_RE.findall(text))


def _check_error_codes(contract: dict, backend: Path, frontend: Path, contract_file: Path) -> list[dict]:
    problems = []
    declared = {str(item.get("code")) for item in contract.get("errorCodes") or [] if isinstance(item, dict)}
    domain_file = backend / "app" / "domain" / "errors.py"
    domain = _domain_error_codes(domain_file)
    if domain is None:
        problems.append(common.problem("BC-05", domain_file, 0, "缺少 ERROR_CODES 常量表"))
    else:
        for code in sorted(declared - domain):
            problems.append(common.problem("BC-05", domain_file, 0, f"契约错误码 {code} 未在 ERROR_CODES 中定义"))
        for code in sorted(domain - declared):
            problems.append(common.problem("BC-05", contract_file, 0, f"ERROR_CODES 中的 {code} 未登记在契约"))
    errors_ts = frontend / "src" / "api" / "errors.ts"
    if frontend.is_dir():
        frontend_codes = _frontend_error_codes(errors_ts)
        if frontend_codes is None:
            problems.append(common.problem("BC-05", errors_ts, 0, "缺少前端错误码文案表"))
        else:
            for code in sorted(declared - frontend_codes):
                problems.append(common.problem("BC-05", errors_ts, 0, f"前端缺少错误码 {code} 的中文文案"))
    return problems


def _versions_from_ast(path: Path, names: tuple[str, ...]) -> dict[str, object]:
    tree = common.parse(path)
    if tree is None:
        return {}
    found: dict[str, object] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in names:
            value = node.value
        elif isinstance(node, ast.Assign):
            targets = [item.id for item in node.targets if isinstance(item, ast.Name)]
            if not set(targets) & set(names):
                continue
            value = node.value
        else:
            continue
        if isinstance(value, ast.Dict):
            for key, item in zip(value.keys, value.values):
                if isinstance(key, ast.Constant) and isinstance(item, ast.Constant):
                    found[str(key.value)] = item.value
    return found


def _plugin_versions() -> dict[str, str]:
    values: dict[str, str] = {}
    for path in (common.PLUGIN_MODEL, common.PLUGIN_FOOTER):
        text = common.read_text(path)
        for name, raw in VERSION_LITERAL_RE.findall(text):
            if name in {"REVIEW_SCHEMA_VERSION", "RUBRIC_VERSION", "RULES_VERSION", "ENGINE_VERSION"}:
                values[name] = raw.strip('"')
    return values


def _check_versions(contract: dict, backend: Path) -> list[dict]:
    problems = []
    declared = contract.get("versions") or {}
    versions_file = backend / "app" / "domain" / "versions.py"
    local = _versions_from_ast(versions_file, ("VERSIONS", "SUPPORTED_VERSIONS"))
    if not local:
        problems.append(common.problem("BC-06", versions_file, 0, "缺少 VERSIONS 常量表"))
    else:
        for key, expected in declared.items():
            if key not in local:
                problems.append(common.problem("BC-06", versions_file, 0, f"缺少版本字段 {key}"))
            elif str(local[key]) != str(expected):
                problems.append(
                    common.problem("BC-06", versions_file, 0, f"{key} 为 {local[key]}，契约要求 {expected}")
                )
    plugin = _plugin_versions()
    mapping = {
        "schemaVersion": "REVIEW_SCHEMA_VERSION",
        "rubricVersion": "RUBRIC_VERSION",
        "rulesVersion": "RULES_VERSION",
        "engineVersion": "ENGINE_VERSION",
    }
    for key, constant in mapping.items():
        expected = declared.get(key)
        actual = plugin.get(constant)
        if expected is None or actual is None:
            problems.append(common.problem("BC-06", common.PLUGIN_MODEL, 0, f"无法读取 {constant} 或契约 {key}"))
        elif str(expected) != str(actual):
            problems.append(
                common.problem("BC-06", common.PLUGIN_MODEL, 0, f"{constant}={actual} 与契约 {key}={expected} 不一致")
            )
    return problems


def _frontend_calls(frontend: Path) -> set[tuple[str, str]]:
    calls: set[tuple[str, str]] = set()
    api_dir = frontend / "src" / "api"
    paths = sorted(api_dir.rglob("*.ts")) if api_dir.is_dir() else []
    for path in paths:
        for method, url in CALL_RE.findall(common.read_text(path)):
            calls.add((method.upper(), _normalize_path(url)))
    return calls


def _check_frontend_calls(contract: dict, frontend: Path) -> list[dict]:
    problems = []
    if not frontend.is_dir():
        return problems
    calls = _frontend_calls(frontend)
    declared = {(str(item.get("method")).upper(), _normalize_path(str(item.get("path")))) for item in _contract_endpoints(contract)}
    for method, path in sorted(calls - declared):
        problems.append(common.problem("BC-07", frontend / "src" / "api", 0, f"前端调用了契约中不存在的 {method} {path}"))
    for item in _contract_endpoints(contract):
        if item.get("client") != "ui":
            continue
        key = (str(item.get("method")).upper(), _normalize_path(str(item.get("path"))))
        if key not in calls:
            problems.append(
                common.problem("BC-07", frontend / "src" / "api", 0, f"契约要求界面调用的 {key[0]} {key[1]} 未在前端出现")
            )
    return problems


def _check_types_snapshot(frontend: Path, openapi_path: Path) -> list[dict]:
    types_file = frontend / "src" / "api" / "types.gen.ts"
    if not types_file.is_file():
        return [common.problem("BC-08", types_file, 0, "缺少 types.gen.ts，运行 --update-contract 后重新生成")]
    text = common.read_text(types_file)
    match = re.search(r"openapi-sha256:\s*([0-9a-f]{64})", text)
    if not match:
        return [common.problem("BC-08", types_file, 0, "types.gen.ts 首行缺少 openapi-sha256 标记")]
    actual = hashlib.sha256(openapi_path.read_bytes()).hexdigest() if openapi_path.is_file() else ""
    if match.group(1) != actual:
        return [common.problem("BC-08", types_file, 0, "types.gen.ts 与当前 OpenAPI 快照不一致")]
    return []


def scan(backend=None, frontend=None, contract_path=None, openapi_path=None) -> list[dict]:
    backend = backend or common.BACKEND
    frontend = frontend or common.FRONTEND
    contract_file = contract_path or common.CONTRACT
    openapi_file = openapi_path or common.OPENAPI

    contract = common.load_json(contract_file)
    problems = _check_contract_shape(contract, contract_file)
    if contract is None:
        return problems
    problems += _check_roles(contract, contract_file)
    problems += _check_csrf(contract, contract_file)
    if not backend.is_dir():
        return problems
    problems += _check_openapi(contract, openapi_file)
    problems += _check_error_codes(contract, backend, frontend, contract_file)
    problems += _check_versions(contract, backend)
    if frontend.is_dir():
        problems += _check_frontend_calls(contract, frontend)
        problems += _check_types_snapshot(frontend, openapi_file)
    return problems


def dump_openapi(backend=None, openapi_path=None) -> Path:
    """从后端应用导出 OpenAPI 快照；仅在 `--update-contract` 时调用。"""
    root = backend or common.BACKEND
    output = openapi_path or common.OPENAPI
    sys.path.insert(0, str(root))
    from app.main import app  # noqa: PLC0415 - 只有该分支需要后端依赖

    snapshot = app.openapi()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> int:
    item = common.parser("G2 契约闸门")
    item.add_argument("--update-contract", action="store_true", help="从后端应用刷新 OpenAPI 快照")
    args = item.parse_args()
    if args.update_contract:
        saved = dump_openapi()
        print(f"saved {common.rel(saved)}")
        return 0
    if common.backend_absent():
        return common.emit("contract", [], skipped=True, as_json=args.json)
    return common.emit("contract", scan(), as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
