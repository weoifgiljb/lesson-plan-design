# -*- coding: utf-8 -*-
"""受控建号入口：给新部署创建第一个管理员（以及可选教师）。

用法：
    py -3 scripts/seed_users.py --admin admin1 --password 'Lesson2026' --name 管理员
    py -3 scripts/seed_users.py --teacher teacher1 --password 'Lesson2026' --name 张老师 --group 计算机

幂等：用户名已存在时只更新口令哈希与角色，不重复插入。口令必须满足
`security.password_problem` 的强度规则（长度不少于 8）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "src" / "backend"
sys.path.insert(0, str(BACKEND))

from app.adapters.db.connection import open_database  # noqa: E402
from app.adapters.db.repo import Repo  # noqa: E402
from app.application import user_service  # noqa: E402
from app.domain import security  # noqa: E402
from app.domain.errors import AppError  # noqa: E402


def _ensure(repo: Repo, username: str, display_name: str, role: str, password: str) -> str:
    problem = security.password_problem(password)
    if problem:
        raise AppError("PAYLOAD_REJECTED", problem)
    existing = repo.user_by_username(username)
    if existing is None:
        repo.insert_user(username, display_name, role, security.hash_password(password))
        return f"created {username} ({role})"
    repo.set_password(int(existing["id"]), security.hash_password(password))
    return f"updated {username} ({role})"


def main() -> int:
    parser = argparse.ArgumentParser(description="创建或重置平台账号")
    parser.add_argument("--admin", help="管理员用户名")
    parser.add_argument("--teacher", help="教师用户名")
    parser.add_argument("--password", required=True, help="口令（不少于 8 位）")
    parser.add_argument("--name", default="", help="显示名，默认与用户名相同")
    parser.add_argument("--group", default="", help="所属教研组（教师用）")
    args = parser.parse_args()
    if not args.admin and not args.teacher:
        parser.error("至少给 --admin 或 --teacher")

    conn = open_database()
    try:
        repo = Repo(conn)
        done = []
        if args.admin:
            done.append(_ensure(repo, args.admin, args.name or args.admin, "admin", args.password))
        if args.teacher:
            done.append(_ensure(repo, args.teacher, args.name or args.teacher, "teacher", args.password))
    finally:
        conn.close()
    for line in done:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
