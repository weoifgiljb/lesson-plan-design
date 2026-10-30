# -*- coding: utf-8 -*-
"""把插件自带的黄金样例导入样例库（幂等）。

需求写的是"15 份样例"，插件仓库当前只带 7 份（`plugins/.../examples/*.json`）。
本脚本把存在的样例全部导入，并打印"库内数量 / 插件数量"，差多少一眼可见。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "backend"))

from app.adapters.db.connection import open_database  # noqa: E402
from app.adapters.db.repo import Repo  # noqa: E402
from app.application import sample_service  # noqa: E402
from app.domain.errors import AppError  # noqa: E402

EXAMPLES = (
    REPO_ROOT
    / "plugins"
    / "lesson-plan-design"
    / "skills"
    / "lesson-plan-design"
    / "examples"
)


def _examples() -> list[Path]:
    return sorted(path for path in EXAMPLES.glob("*.json") if path.name != "index.json")


def main() -> int:
    files = _examples()
    if not files:
        print(f"未找到样例：{EXAMPLES}")
        return 1
    connection = open_database()
    try:
        repo = Repo(connection)
        admin = None
        for user in repo.list_users():
            if str(user["role"]) == "admin":
                admin = user
                break
        if admin is None:
            print("需要先有一个 admin 账号（py -3 scripts/seed_users.py --admin ...）")
            return 1
        created = 0
        skipped = 0
        for path in files:
            data = path.read_bytes()
            try:
                sample_service.create(repo, admin, data)
                created += 1
            except AppError as exc:
                if exc.code != "CONFLICT_STALE":
                    raise
                skipped += 1
        total = repo.count_samples()
    finally:
        connection.close()
    print(f"导入 {created} 份，跳过 {skipped} 份（已存在），库内共 {total} 份")
    print(f"插件样例 {len(files)} 份；需求目标 15 份，缺口 {max(0, 15 - total)} 份")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
