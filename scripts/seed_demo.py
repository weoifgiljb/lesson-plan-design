# -*- coding: utf-8 -*-
"""给本地/联调环境补一批演示数据（幂等，可重复执行）。

    py -3 scripts/seed_demo.py

补的内容（都以 teacher1 为所有者的真实业务数据，走应用服务而不是直接插库）：
- 6 个教学任务（含逾期草稿、四象限分布）
- 3 份教案：用插件黄金样例构造契约包入库；其中 1 份带第 2 版，可看版本差异
- 1 次导出（走门禁并落盘 data/exports/）
- 通知由「逾期 / 多版本 / 导出」自动产生，不直接插库

数据目录与后端一致（`LPP_DATA_DIR`，默认 `<仓库根目录>/data`）。
已存在的任务/教案会跳过，不会覆盖或重复建版本。
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "src" / "backend"
TESTS = BACKEND / "tests"
for entry in (BACKEND, TESTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from app.adapters.db.connection import open_database  # noqa: E402
from app.adapters.db.repo import Repo  # noqa: E402
from app.application import (  # noqa: E402
    export_service,
    ingest_service,
    notification_service,
    task_service,
)
from app.domain.errors import AppError  # noqa: E402
import factories  # noqa: E402  - 测试侧契约包构造器，保证 manifest/哈希按真实字节生成
import support  # noqa: E402  - 测试侧插件审查报告生成器

EXAMPLES = (
    REPO_ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "examples"
)
TEACHER_USERNAME = "teacher1"
TEACHER_DISPLAY_NAME = "张老师"
CLASS_IT = "计算机2301"
CLASS_C = "计算机2302"

# (课程, 周次, 课次, 课题, 班级, 截止日期, 四象限)
TASKS = (
    ("信息技术", 2, 1, "一级考证辅导2", CLASS_IT, "2026-11-10", "urgent_important"),
    ("信息技术", 4, 1, "一级考证辅导6", CLASS_IT, "2026-11-15", "important_not_urgent"),
    ("C语言程序设计", 1, 1, "认识C语言与Dev-C++开发环境", CLASS_C, "2026-12-05", "important_not_urgent"),
    ("C语言程序设计", 2, 1, "数据类型、变量与常量", CLASS_C, "2026-11-18", "urgent_not_important"),
    ("信息技术", 3, 1, "一级考证辅导4", CLASS_IT, "2026-12-10", "urgent_important"),
    ("C语言程序设计", 3, 1, "if单分支与双分支", CLASS_C, "2026-12-20", "important_not_urgent"),
)

# (插件样例, 班级, 授课日期, 是否再造一版)
PLANS = (
    ("信息技术0201.json", CLASS_IT, "2026-11-10", True),
    ("C语言0101.json", CLASS_C, "2026-11-14", False),
    ("C语言0201.json", CLASS_C, "2026-11-18", False),
)

VERSION_TWO_HOMEWORK = "课后完成第22套并自查错题，下节课前提交复盘记录。"


def _plan_content(example: str, class_name: str, teach_date: str) -> dict:
    plan = json.loads((EXAMPLES / example).read_text(encoding="utf-8"))
    # 黄金样例的元信息是空的，导出会因"元信息缺失"告警；补上再入库，产物才可下载
    plan["teacher"] = TEACHER_DISPLAY_NAME
    plan["teachingObject"] = class_name
    plan["teachDate"] = teach_date
    return plan


def _ensure_task(repo: Repo, teacher: dict, row: tuple) -> tuple[bool, str]:
    course, week, session, title, class_name, due, quadrant = row
    existing = repo.find_task(course, week, session, class_name, title)
    if existing is not None:
        return False, f"任务已存在：{title}（#{existing['id']}）"
    result, _created = task_service.create(
        repo,
        teacher,
        {
            "course": course,
            "week": week,
            "session": session,
            "title": title,
            "className": class_name,
            "dueDate": date.fromisoformat(due),
            "quadrant": quadrant,
        },
        ip="127.0.0.1",
        trace_id="seed-demo",
    )
    return True, f"任务已创建：{title}（#{result['taskId']}）"


def _import_package(repo: Repo, owner_id: int, plan: dict, report: dict) -> ingest_service.ImportResult:
    files = factories.build_package(plan, report=report)
    return ingest_service.import_package(
        repo, files=files, owner_id=owner_id, actor_id=owner_id,
        ip="127.0.0.1", trace_id="seed-demo",
    )


def _seed_plan(repo: Repo, teacher: dict, row: tuple) -> tuple[int, int, bool]:
    """返回 (plan_id, 版本数, 是否新建)。已存在的教案整份跳过，避免重复建版本。"""
    example, class_name, teach_date, with_second_version = row
    owner_id = int(teacher["id"])
    plan = _plan_content(example, class_name, teach_date)
    existing = repo.find_plan_by_identity(owner_id, plan)
    if existing is not None:
        return int(existing["id"]), 0, False
    report = support.plugin_report(plan)
    result = _import_package(repo, owner_id, plan, report)
    versions = 1
    if with_second_version:
        second = json.loads(json.dumps(plan, ensure_ascii=False))
        second["activityFlow"]["homework"] = VERSION_TWO_HOMEWORK
        second_report = support.plugin_report(second, round_number=2, previous_report=report)
        _import_package(repo, owner_id, second, second_report)
        versions = 2
    return result.plan_id, versions, True


def _export_latest(repo: Repo, teacher: dict, plan_id: int) -> str:
    versions = repo.list_versions(plan_id)
    if not versions:
        return "无版本可导出"
    try:
        outcome = export_service.create(
            repo, teacher, [int(versions[-1]["version_id"])],
            ip="127.0.0.1", trace_id="seed-demo",
        )
    except AppError as exc:
        return f"导出失败：{exc.code} {exc.message}"
    item = outcome["items"][0]
    if item.get("status") != "succeeded":
        return f"导出失败：{item.get('code')} {item.get('message')}"
    return "成功"


def main() -> int:
    connection = open_database()
    try:
        repo = Repo(connection)
        teacher = repo.user_by_username(TEACHER_USERNAME)
        if teacher is None or teacher.get("active") != 1:
            print(f"缺少启用中的账号 {TEACHER_USERNAME}，先执行：")
            print(f"  py -3 scripts/seed_users.py --teacher {TEACHER_USERNAME} --password 'Lesson2026' --name {TEACHER_DISPLAY_NAME}")
            return 1

        created_tasks = 0
        for row in TASKS:
            created, message = _ensure_task(repo, teacher, row)
            created_tasks += int(created)
            print(message)

        created_plans = 0
        total_versions = 0
        first_plan_id = None
        for row in PLANS:
            plan_id, versions, created = _seed_plan(repo, teacher, row)
            if created:
                created_plans += 1
                total_versions += versions
                print(f"教案已入库：{row[0]} → plan #{plan_id}，{versions} 个版本")
            else:
                print(f"教案已存在，跳过：{row[0]}")
            if first_plan_id is None:
                first_plan_id = plan_id

        export_status = _export_latest(repo, teacher, first_plan_id) if first_plan_id else "无教案"
        notification_service.notify_overdue(repo, teacher)
        counts = {
            name: repo.conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in ("task", "plan", "plan_version", "review", "export_job", "notification")
        }
        print(f"导出：{export_status}")
        print(
            "库内现在："
            + "，".join(f"{name} {total}" for name, total in counts.items())
            + f"；本次新增任务 {created_tasks} 个、教案 {created_plans} 份（{total_versions} 个版本）"
        )
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
