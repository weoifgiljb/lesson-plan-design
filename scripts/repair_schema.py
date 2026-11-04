# -*- coding: utf-8 -*-
"""把早期谱系的库对齐到当前 SCHEMA_VERSION（先备份，再修复）。

用法：
    py -3 scripts/repair_schema.py                # 只检查，不改库
    py -3 scripts/repair_schema.py --apply        # 备份后修复
    py -3 scripts/repair_schema.py --db <path>    # 指定库文件
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "backend"))

from app.adapters.db import repair as repair_mod  # noqa: E402
from app.config import db_path  # noqa: E402


def _backup_database(source: Path, target: Path) -> None:
    """用 sqlite3 在线备份 API 复制：WAL 尚未 checkpoint 时也能拿到完整快照。

    早期版本用 shutil.copy2 只复制主库文件，WAL 里未落盘的事务会静默丢失
    （甚至得到空壳库），对真实库执行 repair 前必须先做可靠备份。
    """
    if Path(f"{source}-wal").exists():
        print("检测到 WAL：使用 sqlite3 在线备份，避免丢失未 checkpoint 的事务")
    src = sqlite3.connect(source)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    check = sqlite3.connect(target)
    try:
        integrity = check.execute("PRAGMA integrity_check").fetchone()[0]
        tables = check.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0]
    finally:
        check.close()
    if integrity != "ok" or int(tables) == 0:
        raise SystemExit(f"备份校验失败：integrity={integrity} tables={tables}")


def main() -> int:
    parser = argparse.ArgumentParser(description="对齐数据库结构到当前版本")
    parser.add_argument("--db", help="数据库文件路径，默认取配置的 data/app.db")
    parser.add_argument("--apply", action="store_true", help="执行修复（默认只检查）")
    args = parser.parse_args()

    target = Path(args.db) if args.db else Path(db_path())
    if not target.exists():
        print(f"数据库不存在：{target}")
        return 2

    conn = sqlite3.connect(target, isolation_level=None)
    try:
        before = repair_mod.inspect(conn)
        print("== 检查 ==")
        print(json.dumps(before, ensure_ascii=False, indent=2))
        if before["version"] > before["target_version"]:
            print(f"库版本 {before['version']} 高于代码支持的 {before['target_version']}，拒绝处理")
            return 3
        if not before["needs_repair"]:
            print("结构已对齐，无需修复")
            return 0
        if not args.apply:
            print("存在缺口；确认后加 --apply 执行（会先备份）")
            return 1

        backup_dir = target.parent / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = backup_dir / f"{target.stem}-{stamp}.db"
        _backup_database(target, backup)
        print(f"已备份：{backup}")

        # 直接对齐到目标结构：迁移器按版本号前进，遇到"版本号跳号 + 部分列已存在"
        # 的库会报 duplicate column，因此这里由 repair 自己收敛（缺表、缺列、缺索引、键不对）。
        log = repair_mod.repair(conn)
        print("== 修复 ==")
        print(json.dumps(log, ensure_ascii=False, indent=2))
        after = repair_mod.inspect(conn)
        print("== 复查 ==")
        print(json.dumps(after, ensure_ascii=False, indent=2))
        return 0 if not after["needs_repair"] else 4
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
