# -*- coding: utf-8 -*-
"""把 `app/domain/error_codes.py` 的错误码目录同步到契约文件。

错误码只在 Python 目录里维护；本脚本负责把它写进 `docs/api/contract.v1.json`，
`tests/test_errors_api.py` 会校验两边一致，避免文档漂移。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "backend"))

from app.domain.error_codes import CATALOG  # noqa: E402

CONTRACT = REPO_ROOT / "docs" / "api" / "contract.v1.json"


def build(contract: dict) -> dict:
    contract["errorCodes"] = [
        {"code": code, "http": int(spec["http"]), "zh": str(spec["zh"]), "scene": str(spec["scene"])}
        for code, spec in CATALOG.items()
    ]
    return contract


def main() -> int:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    CONTRACT.write_text(
        json.dumps(build(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已同步 {len(CATALOG)} 个错误码到 {CONTRACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
