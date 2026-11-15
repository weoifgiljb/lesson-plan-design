# -*- coding: utf-8 -*-
"""环境与数据体检：技能、数据目录、数据库、备份与插件清单。

用法：
    py -3 scripts/doctor.py
    py -3 scripts/doctor.py --json
    py -3 scripts/doctor.py --skills-dir .dsh/skills --data-dir data
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "docs" / "dev" / "skills.lock.json"
DEFAULT_SKILLS = ROOT / ".dsh" / "skills"
DEFAULT_DATA = ROOT / "data"
DEFAULT_PLUGIN = ROOT / "plugins" / "lesson-plan-design"
EXPECTED_SCHEMA_VERSION = 13
EXPECTED_TABLES = 14
PLUGIN_MANIFESTS = (
    ".claude-plugin/plugin.json",
    ".codebuddy-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
    ".qoder-plugin/plugin.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lock_skills(lock_path: Path) -> list[dict[str, str]]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    skills: list[dict[str, str]] = []
    for source in lock.get("sources", []):
        repo = str(source.get("repo") or "")
        commit = str(source.get("commit") or "")
        for name in source.get("skills", []):
            skills.append({"name": str(name), "repo": repo, "commit": commit})
    return skills


def check_skills(lock_path: Path, skills_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not lock_path.is_file():
        return {"ok": False, "errors": [f"缺少锁文件：{lock_path}"], "warnings": [], "count": 0}
    skills = _lock_skills(lock_path)
    installed: dict[str, dict[str, Any]] = {}
    manifest_path = skills_dir / ".installed.json"
    if manifest_path.is_file():
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in raw.get("skills", []):
                if isinstance(item, dict) and item.get("name"):
                    installed[str(item["name"])] = item
        except (OSError, json.JSONDecodeError):
            warnings.append(f"无法读取 {manifest_path}，只按 SKILL.md 判断")
    missing = [item["name"] for item in skills if not (skills_dir / item["name"] / "SKILL.md").is_file()]
    if missing:
        errors.append(f"技能缺失 {len(missing)}/{len(skills)}：{', '.join(missing[:8])}")
        errors.append("安装/修复：py -3 scripts/bootstrap_skills.py --check（或按 docs/setup/cross-device.md 重建）")
    for item in skills:
        name = item["name"]
        skill_path = skills_dir / name / "SKILL.md"
        record = installed.get(name)
        if record and skill_path.is_file():
            expected = str(record.get("sha256") or "")
            if expected and _sha256(skill_path) != expected:
                errors.append(f"技能 {name} 的 SKILL.md 哈希与 .installed.json 不一致")
            if record.get("commit") and item["commit"] and record["commit"] != item["commit"]:
                errors.append(f"技能 {name} 的提交与锁文件不一致：{record['commit']} != {item['commit']}")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "count": len(skills),
        "installed": len(skills) - len(missing),
    }


def _latest_backup(backup_dir: Path) -> str | None:
    if not backup_dir.is_dir():
        return None
    times: list[str] = []
    for path in backup_dir.glob("*/manifest.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get("createdAt")
            if isinstance(value, str):
                times.append(value)
        except (OSError, json.JSONDecodeError):
            continue
    return max(times) if times else None


def check_data(data_dir: Path, backup_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    info: dict[str, Any] = {"dir": data_dir.name, "lastBackupAt": _latest_backup(backup_dir)}
    if not data_dir.is_dir():
        return {"ok": False, "errors": [f"数据目录不存在：{data_dir}"], "warnings": [], "info": info}
    try:
        with tempfile.NamedTemporaryFile(dir=data_dir, prefix=".doctor-", delete=True):
            pass
    except OSError as exc:
        errors.append(f"数据目录不可写：{exc}")
    database = data_dir / "app.db"
    if not database.is_file():
        errors.append("缺少 data/app.db")
        return {"ok": False, "errors": errors, "warnings": warnings, "info": info}
    try:
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        try:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            tables = [
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
            ]
            counts = {
                table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
                for table in tables
            }
        finally:
            connection.close()
    except sqlite3.Error as exc:
        return {"ok": False, "errors": [*errors, f"数据库不可读：{exc}"], "warnings": warnings, "info": info}
    info.update({"schemaVersion": version, "tables": len(tables), "rowCounts": counts})
    if version != EXPECTED_SCHEMA_VERSION:
        errors.append(f"数据库结构版本 {version}，代码期望 {EXPECTED_SCHEMA_VERSION}")
    if len(tables) != EXPECTED_TABLES:
        errors.append(f"数据库表数 {len(tables)}，期望 {EXPECTED_TABLES}")
    if info["lastBackupAt"] is None:
        warnings.append("还没有成功备份；答辩前至少跑一次 py -3 scripts/backup_data.py")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "info": info}


def _command_values(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "command" and isinstance(item, str):
                found.append(item)
            else:
                found.extend(_command_values(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_command_values(item))
    return found


def check_runtime(plugin_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if sys.version_info < (3, 10):
        errors.append(f"Python 版本过低：{sys.version.split()[0]}，需要 3.10+")
    if not shutil.which("soffice") and not Path("C:/Program Files/LibreOffice/program/soffice.exe").is_file():
        errors.append("未发现 LibreOffice(soffice)：DOCX 预览/转 PDF 会失败")
    if importlib.util.find_spec("playwright") is None:
        errors.append("未安装 Playwright：电子书截图技能会失败")
    scripts = plugin_dir / "skills" / "lesson-plan-design" / "scripts"
    if not scripts.is_dir():
        errors.append(f"插件脚本目录不存在：{scripts}")
        return {"ok": False, "errors": errors, "warnings": warnings}
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import lib  # noqa: PLC0415 - 只有体检时才加载插件引擎
    except Exception as exc:  # noqa: BLE001 - 体检边界要给出可读结论
        errors.append(f"插件引擎无法导入：{type(exc).__name__}: {exc}")
    else:
        try:
            checked = lib.check_examples()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"样例校验失败：{type(exc).__name__}: {exc}")
        else:
            if not checked.get("ok"):
                errors.append(f"样例校验失败：{checked.get('errors')}")
            elif int(checked.get("count") or 0) == 0:
                warnings.append("样例数量为 0")
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def check_plugin(plugin_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    manifests: dict[str, Any] = {}
    for relative in PLUGIN_MANIFESTS:
        path = plugin_dir / relative
        if not path.is_file():
            errors.append(f"缺少清单：{relative}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{relative} 无法解析：{exc}")
            continue
        for key in ("name", "version", "description"):
            if not data.get(key):
                errors.append(f"{relative} 缺少字段 {key}")
        skill_path = plugin_dir / str(data.get("skills") or "")
        if not skill_path.exists():
            errors.append(f"{relative} 的 skills 路径不存在：{data.get('skills')}")
        manifests[relative] = data
    commands: list[str] = []
    for relative in (".mcp.json", "mcp.json", "hooks/hooks.json", "hooks/cursor-hooks.json"):
        path = plugin_dir / relative
        if path.is_file():
            try:
                commands.extend(_command_values(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{relative} 无法解析：{exc}")
    if any(command.strip().startswith("python") and not command.strip().startswith("python3") for command in commands):
        errors.append("发现裸 python 命令；统一使用 py -3（见 FR-08）")
    if commands and not any("py" in command for command in commands):
        warnings.append("未发现 py -3 命令，检查宿主兼容性")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "manifests": sorted(manifests),
        "commands": sorted(set(commands)),
    }


def run(*, lock: Path, skills_dir: Path, data_dir: Path, backup_dir: Path, plugin_dir: Path) -> dict[str, Any]:
    checks = {
        "repo": {"ok": (ROOT / "docs").is_dir() and (ROOT / "src" / "backend").is_dir(), "errors": [], "warnings": []},
        "skills": check_skills(lock, skills_dir),
        "data": check_data(data_dir, backup_dir),
        "runtime": check_runtime(plugin_dir),
        "plugin": check_plugin(plugin_dir),
    }
    errors = [f"[{name}] {item}" for name, result in checks.items() for item in result.get("errors", [])]
    warnings = [f"[{name}] {item}" for name, result in checks.items() for item in result.get("warnings", [])]
    return {"ok": not errors, "checks": checks, "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description="环境、数据与插件清单体检")
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--skills-dir", type=Path, default=DEFAULT_SKILLS)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--backup-dir", type=Path, default=Path(os.environ.get("LPP_BACKUP_DIR", str(ROOT / "backups"))))
    parser.add_argument("--plugin-dir", type=Path, default=DEFAULT_PLUGIN)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run(
        lock=args.lock,
        skills_dir=args.skills_dir,
        data_dir=args.data_dir,
        backup_dir=args.backup_dir,
        plugin_dir=args.plugin_dir,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for name, result in payload["checks"].items():
            print(f"{'OK  ' if result.get('ok') else 'FAIL'} {name}")
            for item in result.get("errors", []):
                print("  error:", item)
            for item in result.get("warnings", []):
                print("  warn :", item)
        print(f"\n{'OK' if payload['ok'] else 'FAIL'}：errors={len(payload['errors'])}，warnings={len(payload['warnings'])}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
