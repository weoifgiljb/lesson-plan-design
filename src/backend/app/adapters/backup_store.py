# -*- coding: utf-8 -*-
"""备份文件系统适配：脚本加载、zip 打包与恢复 staging。"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.domain.errors import AppError

ROOT = Path(__file__).resolve().parents[4]
_modules: dict[str, Any] = {}


def _load(name: str) -> Any:
    if name in _modules:
        return _modules[name]
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"lpp_{name}", path)
    if spec is None or spec.loader is None:
        raise AppError("INTERNAL", f"无法加载 {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _modules[name] = module
    return module


def backup_dir() -> Path:
    return Path(os.environ.get("LPP_BACKUP_DIR", str(ROOT / "backups")))


def data_dir() -> Path:
    return Path(os.environ.get("LPP_DATA_DIR", str(ROOT / "data")))


def _safe(name: str) -> Path:
    """快照名 → 备份根下的路径：用"包含性检查"守住越界，而不是 ASCII 白名单（中文标签要可用）。"""
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise AppError("BACKUP_INVALID", "快照名称非法")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise AppError("BACKUP_INVALID", "快照名称非法")
    if Path(name).name != name or "/" in name or "\\" in name:
        raise AppError("BACKUP_INVALID", "快照名称越界")
    path = backup_dir() / name
    if path.resolve().parent != backup_dir().resolve():
        raise AppError("BACKUP_INVALID", "快照名称越界")
    return path


def _manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AppError("BACKUP_INVALID", "快照 manifest 无法解析") from exc


def _zip_path(path: Path) -> Path:
    """`shutil.make_archive(<path>, "zip")` 的产物是 `<path>.zip`，不能用 with_suffix
    （名称里的点，如 `v1.0`，会被当后缀吃掉）。命名规则只在 scripts/backup_data.py 维护一份。"""
    return _load("backup_data").zip_path_for(path)


def list_snapshots() -> dict[str, Any]:
    items = []
    root = backup_dir()
    if root.is_dir():
        for path in sorted(root.iterdir(), reverse=True):
            if not path.is_dir() or not (path / "manifest.json").is_file():
                continue
            try:
                manifest = _manifest(path)
            except AppError:
                continue
            items.append(
                {
                    "name": path.name,
                    "label": manifest.get("label") or "",
                    "createdAt": manifest.get("createdAt"),
                    "schemaVersion": manifest.get("schemaVersion"),
                    "rows": manifest.get("database", {}).get("rowCounts", {}),
                    "files": manifest.get("totals", {}).get("files", 0),
                    "bytes": manifest.get("totals", {}).get("bytes", 0),
                    "hasZip": _zip_path(path).is_file(),
                }
            )
    return {"items": items, "total": len(items)}


def create(label: str) -> dict[str, Any]:
    module = _load("backup_data")
    try:
        # 标签白名单只在 scripts/backup_data.py 维护一份；这里只做错误码翻译
        result = module.create_snapshot(data_dir(), backup_dir(), label=label.strip() or "manual", make_zip=True)
    except FileNotFoundError as exc:
        raise AppError("DATA_MISSING", "数据目录缺少 app.db") from exc
    except module.LabelError as exc:
        raise AppError("PAYLOAD_REJECTED", str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - 适配层把脚本异常翻译为错误码
        raise AppError("BACKUP_INVALID", f"备份失败：{type(exc).__name__}") from exc
    return {"name": Path(str(result["path"])).name, "path": result["path"], "zip": result.get("zip")}


def archive(name: str) -> tuple[Path, str]:
    path = _safe(name)
    if not (path / "manifest.json").is_file():
        raise AppError("BACKUP_INVALID", "快照不存在")
    zip_path = _zip_path(path)
    if not zip_path.is_file():
        shutil.make_archive(str(path), "zip", root_dir=path)
    return zip_path, f"{name}.zip"


def restore(name: str) -> dict[str, Any]:
    snapshot = _safe(name)
    if not snapshot.is_dir():
        raise AppError("BACKUP_INVALID", "快照不存在")
    module = _load("restore_data")
    target: Path | None = None
    try:
        manifest = module.verify_snapshot(snapshot)
        target = data_dir().parent / f"data-restore-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        if target.exists():
            raise AppError("RESTORE_CONFLICT", "恢复目标已存在，请稍后重试")
        pre = _load("backup_data").create_snapshot(data_dir(), backup_dir(), label="pre-restore", make_zip=True)
        rows = module.restore_snapshot(snapshot, target, force=False)
    except FileNotFoundError as exc:
        raise AppError("DATA_MISSING", "当前 data/app.db 缺失，无法生成前置快照") from exc
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 - 适配层把恢复异常翻译为错误码
        if target is not None:
            shutil.rmtree(target, ignore_errors=True)
        raise AppError("BACKUP_INVALID", f"恢复失败：{type(exc).__name__}") from exc
    return {"snapshot": snapshot.name, "target": str(target), "rows": rows, "preRestore": pre["path"], "schemaVersion": manifest.get("schemaVersion")}
