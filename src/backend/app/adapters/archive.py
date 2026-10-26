# -*- coding: utf-8 -*-
"""zip 契约包安全解包：路径规范化、白名单、大小与条目数限制。

这是唯一允许消费不可信 zip 的边界，也是唯一在此捕获 zip 解析错误的地方。
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path, PurePosixPath

from app.config import (
    ALLOWED_PACKAGE_SUFFIXES,
    MANIFEST_NAME,
    MAX_PACKAGE_BYTES,
    MAX_PACKAGE_FILES,
    max_package_bytes,
)
from app.domain.errors import AppError

SYMLINK_MODE = 0o120000


def normalize_entry(name: str) -> str:
    if not isinstance(name, str) or not name.strip() or "\x00" in name:
        raise AppError("PAYLOAD_REJECTED", "zip 条目名为空或非法")
    normalized = name.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if path.is_absolute() or normalized.startswith("/"):
        raise AppError("PAYLOAD_REJECTED", f"zip 条目不得为绝对路径：{name}")
    parts = [part for part in path.parts if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise AppError("PAYLOAD_REJECTED", f"zip 条目含非法路径段：{name}")
    return PurePosixPath(*parts).as_posix()


def safe_join(root: Path, name: str) -> Path:
    normalized = normalize_entry(name)
    target = (root / normalized).resolve()
    if not target.is_relative_to(root.resolve()):
        raise AppError("PAYLOAD_REJECTED", f"zip 条目越界：{name}")
    return target


def read_json(files: dict[str, bytes], name: str) -> tuple[dict | None, str | None]:
    """从已解包的契约包里读一个 JSON 对象；失败返回 (None, 原因)。"""
    raw = files.get(name)
    if raw is None:
        return None, f"契约包缺少 {name}"
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, f"{name} 不是合法 JSON"
    if not isinstance(data, dict):
        return None, f"{name} 必须是 JSON 对象"
    return data, None


def read_package(data: bytes) -> dict[str, bytes]:
    limit = max_package_bytes()
    if limit <= 0:
        limit = MAX_PACKAGE_BYTES
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise AppError("PAYLOAD_REJECTED", "契约包为空")
    if len(data) > limit:
        raise AppError("PAYLOAD_TOO_LARGE", f"契约包超过 {limit} 字节")
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise AppError("PAYLOAD_REJECTED", "契约包不是合法 zip")
    return _read_entries(_open(io.BytesIO(data)), limit)


def _open(buffer: io.BytesIO) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(buffer)
    except (zipfile.BadZipFile, OSError) as exc:
        raise AppError("PAYLOAD_REJECTED", f"契约包解析失败：{exc}") from exc


def _check_entry(info: zipfile.ZipInfo, seen: set[str], limit: int, total: int) -> int:
    name = normalize_entry(info.filename)
    if name in seen:
        raise AppError("PAYLOAD_REJECTED", f"zip 重复条目：{name}")
    if (info.external_attr >> 16) & 0o170000 == SYMLINK_MODE:
        raise AppError("PAYLOAD_REJECTED", f"zip 条目不得为符号链接：{name}")
    if not name.lower().endswith(ALLOWED_PACKAGE_SUFFIXES):
        raise AppError("PAYLOAD_REJECTED", f"zip 条目类型不在白名单：{name}")
    accumulated = total + int(info.file_size)
    if accumulated > limit:
        raise AppError("PAYLOAD_TOO_LARGE", f"zip 解压后超过 {limit} 字节")
    return accumulated


def _read_one(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    try:
        return archive.read(info)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise AppError("PAYLOAD_REJECTED", f"契约包条目解析失败：{info.filename}") from exc


def _read_entries(archive: zipfile.ZipFile, limit: int) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    seen: set[str] = set()
    total = 0
    infos = archive.infolist()
    if len(infos) > MAX_PACKAGE_FILES:
        archive.close()
        raise AppError("PAYLOAD_REJECTED", f"zip 条目数超过 {MAX_PACKAGE_FILES}")
    for info in infos:
        if info.is_dir():
            continue
        name = normalize_entry(info.filename)
        total = _check_entry(info, seen, limit, total)
        seen.add(name)
        files[name] = _read_one(archive, info)
    archive.close()
    if MANIFEST_NAME not in files:
        raise AppError("PAYLOAD_REJECTED", "契约包缺少 manifest.json")
    return files
