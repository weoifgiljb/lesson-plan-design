# -*- coding: utf-8 -*-
"""从 OpenAPI 快照生成前端类型；首行写 openapi-sha256，供 BC-08 比对。"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "docs" / "api" / "openapi.v1.json"
OUTPUT = ROOT / "src" / "frontend" / "src" / "api" / "types.gen.ts"


def _name(value: str) -> str:
    parts = re.split(r"[^0-9A-Za-z]+", value)
    name = "".join(part[:1].upper() + part[1:] for part in parts if part)
    if not name:
        return "Unnamed"
    if name[0].isdigit():
        name = "T" + name
    return name


def _ts_type(schema: dict[str, Any] | None, indent: int = 0) -> str:
    if not schema:
        return "unknown"
    if "$ref" in schema:
        return _name(str(schema["$ref"]).rsplit("/", 1)[-1])
    if "allOf" in schema:
        return " & ".join(_ts_type(item, indent) for item in schema["allOf"])
    if "oneOf" in schema or "anyOf" in schema:
        key = "oneOf" if "oneOf" in schema else "anyOf"
        return " | ".join(_ts_type(item, indent) for item in schema[key])
    if "enum" in schema:
        values = schema["enum"]
        if all(isinstance(item, (str, int, float, bool)) for item in values):
            return " | ".join(json.dumps(item, ensure_ascii=False) for item in values)
    kind = schema.get("type")
    if kind == "array":
        return f"{_ts_type(schema.get('items'), indent)}[]"
    if kind == "object" or "properties" in schema:
        properties = schema.get("properties") or {}
        if not properties:
            extra = schema.get("additionalProperties")
            if isinstance(extra, dict):
                return f"Record<string, {_ts_type(extra, indent)}>"
            return "Record<string, unknown>"
        required = set(schema.get("required") or [])
        pad = " " * (indent + 2)
        lines = ["{"]
        for key, value in properties.items():
            optional = "" if key in required else "?"
            lines.append(f"{pad}{key}{optional}: {_ts_type(value, indent + 2)}")
        lines.append(" " * indent + "}")
        return "\n".join(lines)
    if kind == "integer" or kind == "number":
        return "number"
    if kind == "boolean":
        return "boolean"
    if kind == "string":
        return "string"
    if kind == "null":
        return "null"
    return "unknown"


def build(openapi: dict[str, Any], digest: str) -> str:
    lines = [
        f"// openapi-sha256: {digest}",
        "// 由 scripts/gen_frontend_types.py 生成，请勿手改。",
        "",
    ]
    schemas = openapi.get("components", {}).get("schemas", {}) or {}
    used: dict[str, str] = {}
    for key, schema in schemas.items():
        name = _name(key)
        if name in used:
            continue
        used[name] = key
        lines.append(f"export interface {name} {_ts_type(schema)}")
        lines.append("")
    for path in sorted(openapi.get("paths", {})):
        for method in sorted(openapi["paths"][path]):
            operation = openapi["paths"][path][method]
            operation_id = operation.get("operationId") or f"{method}_{path}"
            name = _name(operation_id) + "Response"
            lines.append(f"export type {name} = Record<string, unknown>")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openapi", type=Path, default=OPENAPI)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    openapi = json.loads(args.openapi.read_text(encoding="utf-8"))
    digest = hashlib.sha256(args.openapi.read_bytes()).hexdigest()
    content = build(openapi, digest)
    if args.check:
        if not args.out.is_file():
            raise SystemExit(f"缺少 {args.out}")
        if args.out.read_text(encoding="utf-8") != content:
            raise SystemExit("types.gen.ts 与 OpenAPI 快照不一致，请重新生成")
        print("types.gen.ts 已是最新")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(content, encoding="utf-8")
    print(f"saved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
