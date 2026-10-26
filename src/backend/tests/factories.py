# -*- coding: utf-8 -*-
"""构造测试用契约包：manifest 的哈希全部按真实字节计算。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from support import plugin_report

MEDIA_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c63000100000500010d0a2db4"
    "0000000049454e44ae426082"
)


def dump(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build_package(
    plan: dict,
    *,
    report: dict | None = None,
    with_media: bool = True,
    manifest_mutator=None,
    plan_bytes: bytes | None = None,
    report_bytes: bytes | None = None,
) -> dict[str, bytes]:
    actual_report = report if report is not None else plugin_report(plan)
    plan_raw = plan_bytes if plan_bytes is not None else dump(plan)
    report_raw = report_bytes if report_bytes is not None else dump(actual_report)
    files: dict[str, bytes] = {"plan.json": plan_raw, "plan.review.json": report_raw}
    if with_media:
        files["media/page-003.png"] = MEDIA_BYTES
    entries = [
        {"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
        for name, data in sorted(files.items())
    ]
    manifest = {
        "contractVersion": "1",
        "planHash": hashlib.sha256(
            json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "reportHash": hashlib.sha256(report_raw).hexdigest(),
        "schemaVersion": actual_report.get("schemaVersion", 1),
        "rubricVersion": actual_report.get("rubricVersion", "1.0"),
        "createdAt": "2026-10-26T00:00:00+00:00",
        "files": entries,
    }
    if manifest_mutator is not None:
        manifest_mutator(manifest)
    files["manifest.json"] = dump(manifest)
    return files


def rewrite_manifest(files: dict[str, bytes], mutator) -> dict[str, bytes]:
    manifest = json.loads(files["manifest.json"].decode("utf-8"))
    mutator(manifest)
    updated = dict(files)
    updated["manifest.json"] = dump(manifest)
    return updated


def write_zip(path: Path, files: dict[str, bytes]) -> Path:
    import zipfile

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    return path
