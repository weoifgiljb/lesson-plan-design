# -*- coding: utf-8 -*-
"""错误码单一来源校验：契约 errorCodes 必须与 domain/error_codes.py 完全一致。

挂进 `scripts/run_backend_gate.py` 的 contract 阶段后，前端文案漂移、漏码、HTTP 不一致都会变成 block。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "api" / "contract.v1.json"

if str(ROOT / "src" / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "src" / "backend"))

from app.domain.error_codes import CATALOG  # noqa: E402


def main() -> int:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    entries = payload.get("errorCodes") or []
    blocks: list[dict[str, object]] = []

    seen = {item.get("code") for item in entries}
    for code in CATALOG:
        if code not in seen:
            blocks.append(
                {
                    "rule": "BC-09",
                    "file": str(CONTRACT.relative_to(ROOT)),
                    "line": 0,
                    "detail": f"契约缺少错误码 {code}（error_codes.CATALOG 有）",
                    "severity": "block",
                }
            )

    by_code = {item.get("code"): item for item in entries}
    for code, spec in CATALOG.items():
        item = by_code.get(code)
        if item is None:
            continue
        if int(item.get("http", 0)) != int(spec["http"]):
            blocks.append(
                {
                    "rule": "BC-09",
                    "file": str(CONTRACT.relative_to(ROOT)),
                    "line": 0,
                    "detail": f"{code} 的 HTTP 状态不一致：契约 {item.get('http')} vs 目录 {spec['http']}",
                    "severity": "block",
                }
            )
        if str(item.get("zh", "")) != str(spec["zh"]):
            blocks.append(
                {
                    "rule": "BC-09",
                    "file": str(CONTRACT.relative_to(ROOT)),
                    "line": 0,
                    "detail": f"{code} 的中文文案不一致：契约「{item.get('zh')}」vs 目录「{spec['zh']}」",
                    "severity": "block",
                }
            )

    for code in sorted(code for code in seen if code not in CATALOG):
        blocks.append(
            {
                "rule": "BC-09",
                "file": str(CONTRACT.relative_to(ROOT)),
                "line": 0,
                "detail": f"契约里有目录中不存在的错误码 {code}",
                "severity": "block",
            }
        )

    print(json.dumps({"gate": "errors", "ok": not blocks, "blocks": blocks, "warns": []}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
