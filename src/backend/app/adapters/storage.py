# -*- coding: utf-8 -*-
"""文件存储：安全路径、内容哈希与原子写。"""
from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from pathlib import Path

from app.config import exports_dir, files_dir
from app.domain.errors import AppError


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise AppError("PAYLOAD_REJECTED", "存储路径为空")
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise AppError("PAYLOAD_REJECTED", f"存储路径越界：{relative}")
    return candidate


def write_bytes(root: Path, relative: str, data: bytes) -> Path:
    target = safe_path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.tmp-{uuid.uuid4().hex}")
    temporary.write_bytes(data)
    os.replace(temporary, target)
    return target


def read_bytes(root: Path, relative: str) -> bytes:
    return safe_path(root, relative).read_bytes()


def disk_status() -> str:
    target = files_dir()
    if target.exists():
        return "ok" if os.access(target, os.W_OK) else "down"
    return "ok" if os.access(target.parent, os.W_OK) else "down"


def store_version_files(plan_id: int, version_no: int, files: dict[str, bytes]) -> dict[str, str]:
    """把契约包内文件原样落到 files/plans/<id>/<version>/，返回 名称 -> sha256。

    任一条写失败就把本次已写的目录清掉，避免失败后残留半套文件（评审 P19-1）。
    """
    root = files_dir()
    base = f"plans/{plan_id}/{version_no}"
    stored: dict[str, str] = {}
    try:
        for name, data in files.items():
            write_bytes(root, f"{base}/{name}", data)
            stored[name] = sha256_bytes(data)
    except Exception:
        remove_version_files(plan_id, version_no)
        raise
    return stored


def remove_version_files(plan_id: int, version_no: int) -> None:
    target = files_dir() / f"plans/{plan_id}/{version_no}"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


def export_path(job_id: int) -> Path:
    return exports_dir() / f"{job_id}.docx"


def read_export(job_id: int) -> bytes:
    return export_path(job_id).read_bytes()
