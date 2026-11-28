# -*- coding: utf-8 -*-
"""一键导出双端契约包（contract / OpenAPI / 前端类型）。"""
from __future__ import annotations

import argparse
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    Path("docs/api/contract.v1.json"),
    Path("docs/api/openapi.v1.json"),
    Path("src/frontend/src/api/types.gen.ts"),
)


def export_contracts(root: Path, output: Path) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in FILES:
            path = root / relative
            if not path.is_file():
                raise FileNotFoundError(f"契约文件缺失：{relative}")
            archive.write(path, relative.as_posix())
    return {
        "ok": True,
        "path": str(output),
        "files": [item.as_posix() for item in FILES],
        "bytes": output.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出契约包")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    output = args.out or ROOT / "output" / f"contracts-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.zip"
    result = export_contracts(ROOT, output)
    print(f"contracts: {result['path']} ({result['bytes']} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
