# -*- coding: utf-8 -*-
"""按 skills.lock.json 重建 24 个技能：克隆/缓存、校验、回滚。

用法：
    py -3 scripts/bootstrap_skills.py --check
    py -3 scripts/bootstrap_skills.py --offline
    py -3 scripts/bootstrap_skills.py --only qa,test-strategy
    py -3 scripts/bootstrap_skills.py --global
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "docs" / "dev" / "skills.lock.json"
DEFAULT_TARGET = ROOT / ".dsh" / "skills"
INSTALLED_NAME = ".installed.json"


class BootstrapError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_lock(lock_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapError(3, f"锁文件无法读取：{exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise BootstrapError(3, "锁文件缺少 sources")
    return data


def lock_skills(lock: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for source in lock.get("sources", []):
        for name in source.get("skills", []):
            items.append(
                {
                    "name": str(name),
                    "repo": str(source.get("repo") or ""),
                    "commit": str(source.get("commit") or ""),
                    "sourcePath": str(source.get("sourcePath") or ""),
                    "originalPath": str((source.get("originalPaths") or {}).get(name) or ""),
                }
            )
    return items


def _cache_dir(cache: Path, repo: str) -> Path:
    stamp = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:12]
    return cache / stamp


def _ensure_repo(cache: Path, repo: str, commit: str, *, offline: bool) -> Path:
    path = _cache_dir(cache, repo)
    if (path / ".git").is_dir():
        if not offline:
            subprocess.run(["git", "-C", str(path), "checkout", "--quiet", commit], check=True)
        return path
    if offline:
        raise BootstrapError(4, f"离线且没有缓存：{repo}")
    cache.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["git", "clone", "--quiet", repo, str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "checkout", "--quiet", commit], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        shutil.rmtree(path, ignore_errors=True)
        raise BootstrapError(4, f"来源不可用：{repo}（{exc}）") from exc
    return path


def _skill_source(repo_dir: Path, item: dict[str, str]) -> Path:
    if item["originalPath"]:
        return repo_dir / item["originalPath"]
    return repo_dir / item["sourcePath"] / item["name"]


def install(
    lock_path: Path,
    target: Path,
    *,
    cache: Path,
    offline: bool = False,
    only: set[str] | None = None,
) -> dict[str, Any]:
    lock = load_lock(lock_path)
    skills = [item for item in lock_skills(lock) if not only or item["name"] in only]
    if not skills:
        raise BootstrapError(3, "没有匹配的技能")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.tmp-{uuid.uuid4().hex}"
    backup = target.parent / f".{target.name}.bak-{uuid.uuid4().hex}"
    installed: list[dict[str, str]] = []
    try:
        temporary.mkdir()
        for item in skills:
            repo_dir = _ensure_repo(cache, item["repo"], item["commit"], offline=offline)
            source = _skill_source(repo_dir, item)
            if not (source / "SKILL.md").is_file():
                raise BootstrapError(3, f"技能目录缺少 SKILL.md：{item['name']}")
            destination = temporary / item["name"]
            shutil.copytree(source, destination)
            installed.append(
                {
                    "name": item["name"],
                    "repo": item["repo"],
                    "commit": item["commit"],
                    "sha256": _sha256(destination / "SKILL.md"),
                }
            )
        manifest = {
            "formatVersion": 1,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "skills": installed,
        }
        (temporary / INSTALLED_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        if target.exists():
            target.replace(backup)
        temporary.replace(target)
        shutil.rmtree(backup, ignore_errors=True)
        return {"ok": True, "target": str(target), "count": len(installed), "skills": installed}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        if backup.exists() and not target.exists():
            backup.replace(target)
        raise


def check(lock_path: Path, target: Path) -> dict[str, Any]:
    lock = load_lock(lock_path)
    expected = lock_skills(lock)
    manifest_path = target / INSTALLED_NAME
    errors: list[str] = []
    if not manifest_path.is_file():
        errors.append(f"缺少安装清单：{manifest_path}")
        return {"ok": False, "count": 0, "expected": len(expected), "errors": errors}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"安装清单无法解析：{exc}")
        return {"ok": False, "count": 0, "expected": len(expected), "errors": errors}
    installed = {str(item.get("name")): item for item in manifest.get("skills", []) if isinstance(item, dict)}
    for item in expected:
        record = installed.get(item["name"])
        skill_path = target / item["name"] / "SKILL.md"
        if record is None:
            errors.append(f"未安装：{item['name']}")
            continue
        if not skill_path.is_file():
            errors.append(f"缺少 SKILL.md：{item['name']}")
            continue
        if record.get("sha256") != _sha256(skill_path):
            errors.append(f"哈希不一致：{item['name']}")
        if record.get("commit") != item["commit"]:
            errors.append(f"提交不一致：{item['name']}")
    return {"ok": not errors, "count": len(installed), "expected": len(expected), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="按锁文件重建/检查技能")
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--skills-dir", type=Path, default=None)
    parser.add_argument("--cache-dir", type=Path, default=Path(os.environ.get("LPP_SKILLS_CACHE", str(Path.home() / ".cache" / "lpp-skills"))))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--only", default="")
    parser.add_argument("--global", dest="global_install", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    target = args.skills_dir or (Path.home() / ".dsh" / "skills" if args.global_install else DEFAULT_TARGET)
    try:
        if args.check:
            payload = check(args.lock, target)
            code = 0 if payload["ok"] else 3
        else:
            only = {item.strip() for item in args.only.split(",") if item.strip()} or None
            payload = install(args.lock, target, cache=args.cache_dir, offline=args.offline, only=only)
            code = 0
    except BootstrapError as exc:
        payload = {"ok": False, "code": exc.code, "error": exc.message}
        code = exc.code
    except (OSError, subprocess.CalledProcessError) as exc:
        payload = {"ok": False, "code": 5, "error": str(exc)}
        code = 5
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif payload.get("ok"):
        if args.check:
            print(f"skills {payload['count']}/{payload['expected']} ok：{target}")
        else:
            print(f"installed {payload['count']} skills -> {target}")
    else:
        print(f"FAIL {payload.get('error') or '；'.join(payload.get('errors', []))}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
