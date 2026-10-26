# -*- coding: utf-8 -*-
"""manifest 解析与文件哈希校验：纯函数，返回 Verdict。"""
from __future__ import annotations

import hashlib
from pathlib import PurePosixPath
from typing import Any

from app.domain.verdict import Verdict, fail

REQUIRED_MANIFEST = (
    "contractVersion",
    "planHash",
    "reportHash",
    "schemaVersion",
    "rubricVersion",
    "createdAt",
    "files",
)
PLAN_FILE = "plan.json"
REPORT_FILE = "plan.review.json"
MANIFEST_FILE = "manifest.json"
MEDIA_PREFIX = "media/"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_path(path: Any) -> str | None:
    if not isinstance(path, str) or not path.strip() or "\x00" in path:
        return None
    text = path.replace("\\", "/").strip()
    candidate = PurePosixPath(text)
    if candidate.is_absolute() or text.startswith("/"):
        return None
    parts = [part for part in candidate.parts if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return None
    return PurePosixPath(*parts).as_posix()


def check_shape(manifest: dict[str, Any]) -> Verdict | None:
    missing = [key for key in REQUIRED_MANIFEST if key not in manifest]
    if missing:
        return fail("PAYLOAD_REJECTED", "manifest 缺少必要字段", {"missing": missing})
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        return fail("PAYLOAD_REJECTED", "manifest.files 必须是非空数组")
    seen: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            return fail("PAYLOAD_REJECTED", "manifest.files 条目必须是对象")
        path = normalize_path(item.get("path"))
        if path is None:
            return fail("PAYLOAD_REJECTED", f"manifest 文件路径非法：{item.get('path')!r}")
        if path in seen:
            return fail("PAYLOAD_REJECTED", f"manifest 文件路径重复：{path}")
        seen.add(path)
        digest = item.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            return fail("PAYLOAD_REJECTED", f"manifest 哈希格式非法：{path}")
        size = item.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            return fail("PAYLOAD_REJECTED", f"manifest 文件大小非法：{path}")
    return None


def _missing(path: str) -> Verdict:
    if path.startswith(MEDIA_PREFIX):
        return fail("MEDIA_MISSING", f"媒体文件缺失：{path}", {"path": path})
    return fail("PAYLOAD_REJECTED", f"契约包缺少声明文件：{path}", {"path": path})


def _mismatch(path: str) -> Verdict:
    if path == PLAN_FILE:
        return fail("HASH_MISMATCH", "教案内容哈希不符", {"path": path})
    if path == REPORT_FILE:
        return fail("REPORT_INCONSISTENT", "审查报告哈希不符", {"path": path})
    if path.startswith(MEDIA_PREFIX):
        return fail("MEDIA_MISSING", f"媒体文件哈希不符：{path}", {"path": path})
    return fail("PAYLOAD_REJECTED", f"文件哈希不符：{path}", {"path": path})


def verify_files(manifest: dict[str, Any], files: dict[str, bytes]) -> Verdict | None:
    declared = {normalize_path(item["path"]): item for item in manifest["files"]}
    for path, item in declared.items():
        data = files.get(path)
        if data is None:
            return _missing(path)
        if sha256_bytes(data) != item["sha256"]:
            return _mismatch(path)
    extra = set(files) - set(declared) - {MANIFEST_FILE}
    if extra:
        return fail("PAYLOAD_REJECTED", "契约包含未声明的文件", {"extra": sorted(extra)})
    return None
