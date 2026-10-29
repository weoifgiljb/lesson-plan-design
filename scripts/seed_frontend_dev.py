# -*- coding: utf-8 -*-
"""为本地前端联调创建账号与可选演示数据。

仅用于开发环境：
- 默认数据目录 <仓库根目录>/data（gitignored），可用 LPP_DATA_DIR 或 --data-dir 覆盖；
- 不修改后端源码、不写生产数据；
- 账号密码只用于 dev，生产首次管理员由运维命令创建，不允许公开自助注册。
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.adapters import archive  # noqa: E402
from app.adapters.db.connection import open_database  # noqa: E402
from app.adapters.db.repo import Repo  # noqa: E402
from app.application import ingest_service, sample_service, task_service  # noqa: E402
from app.config import data_dir  # noqa: E402
from app.domain import library, security  # noqa: E402

PASSWORD = "Lesson2026"
DEMO_PACKAGE = ROOT / "tests" / "fixtures" / "dual-end" / "platform" / "packages" / "valid-0201.zip"
DEMO_PLAN_JSON = ROOT / "tests" / "fixtures" / "dual-end" / "platform" / "valid-package" / "plan.json"

ACCOUNTS = (
    ("teacher01", "张老师", "teacher", "计算机"),
    ("lead01", "王组长", "lead", "计算机"),
    ("admin01", "管理员", "admin", ""),
)


def ensure_accounts(repo: Repo) -> dict[str, dict]:
    result = {}
    for username, display_name, role, group_name in ACCOUNTS:
        user = repo.user_by_username(username)
        if user is None:
            user_id = repo.insert_user(
                username,
                display_name,
                role,
                security.hash_password(PASSWORD),
                group_name,
            )
            print(f"created user {username} (id={user_id}, role={role})")
            user = repo.user_by_username(username)
        else:
            print(f"reuse user {username} (id={user['id']}, role={user['role']})")
        if user is not None:
            result[username] = user
    return result


def seed_demo(repo: Repo, users: dict[str, dict]) -> None:
    teacher = users.get("teacher01")
    admin = users.get("admin01")
    if teacher is None or admin is None:
        raise RuntimeError("teacher01/admin01 未创建成功")

    scope = library.scope_for(teacher)
    rows, total = repo.list_plans(scope, {}, 1, 0)
    if total == 0:
        package = DEMO_PACKAGE.read_bytes()
        files = archive.read_package(package)
        result = ingest_service.import_package(
            repo,
            files=files,
            owner_id=int(teacher["id"]),
            actor_id=int(teacher["id"]),
            trace_id="seed-demo",
        )
        print(f"imported demo plan planId={result.plan_id} version={result.version_no} review={result.review_id}")
        rows, total = repo.list_plans(scope, {}, 1, 0)
    else:
        print(f"reuse {total} teacher plan(s)")

    if total == 0:
        print("warning: no plan imported; skip task/sample demo")
        return

    _, task_total = repo.list_tasks(scope, {}, 1, 0)
    if task_total == 0:
        task = task_service.create(
            repo,
            teacher,
            {
                "course": "信息技术",
                "week": 2,
                "session": 1,
                "title": "一级考证辅导2",
                "className": "计算机2301",
                "dueDate": date.today() + timedelta(days=2),
            },
            trace_id="seed-demo",
        )
        print(f"created demo task taskId={task['taskId']}")
    else:
        print(f"reuse {task_total} task(s)")

    _, sample_total = repo.list_samples({}, 1, 0)
    if sample_total == 0:
        plan_bytes = DEMO_PLAN_JSON.read_bytes()
        sample = sample_service.create(repo, admin, plan_bytes, trace_id="seed-demo")
        print(f"created demo sample sampleId={sample['sampleId']}")
    else:
        print(f"reuse {sample_total} sample(s)")


def main() -> int:
    parser = argparse.ArgumentParser(description="创建前端联调账号与演示数据（仅 dev）")
    parser.add_argument("--data-dir", default="", help="覆盖 LPP_DATA_DIR，默认仓库 data/")
    parser.add_argument("--with-demo", action="store_true", help="导入有效契约包、任务与样例")
    args = parser.parse_args()
    if args.data_dir:
        os.environ["LPP_DATA_DIR"] = str(Path(args.data_dir).resolve())

    print(f"data dir: {data_dir()}")
    repo = Repo(open_database(), threading.Lock())
    try:
        users = ensure_accounts(repo)
        if args.with_demo:
            seed_demo(repo, users)
    finally:
        repo.close()

    print("")
    print("dev accounts (password %s):" % PASSWORD)
    for username, _, role, _ in ACCOUNTS:
        print(f"  {username:10s} {role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
