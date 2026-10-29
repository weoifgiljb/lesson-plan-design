# -*- coding: utf-8 -*-
"""统计摘要 API：9 项指标、分子/分母、范围与软删除口径。"""
from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, load_json_bytes, read_package_dir, tempdir

from app.adapters import engine
from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


def make_report(plan_hash: str, *, status: str = "passed", findings: list | None = None) -> dict:
    finding_list = findings or []
    return {
        "schemaVersion": 1,
        "rubricVersion": "1.0",
        "toolVersion": "1.0.0",
        "planHash": plan_hash,
        "planSnapshot": None,
        "round": 1,
        "duplicateReview": False,
        "reviewer": "native_subagent",
        "independence": "native_subagent",
        "reviewedAt": "2026-10-27T00:00:00+00:00",
        "structuralValidation": {"ok": True},
        "findings": finding_list,
        "overrides": [],
        "repairHistory": [],
        "attestation": "no_counterexample" if status == "passed" else None,
        "status": status,
        "conclusion": "",
    }


class TestStatsApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        connection = open_database(self.db_file)
        self.repo = Repo(connection)
        self.teacher1 = self.repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD), "计算机")
        self.teacher2 = self.repo.insert_user("teacher2", "李老师", "teacher", security.hash_password(PASSWORD), "英语")
        self.lead1 = self.repo.insert_user("lead1", "王组长", "lead", security.hash_password(PASSWORD), "计算机")
        self.admin = self.repo.insert_user("admin1", "管理员", "admin", security.hash_password(PASSWORD), "")
        self._seed()
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.repo.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _plan(
        self, owner: int, title: str, course: str = "信息技术", *, content: str = "{}", plan_hash: str | None = None
    ) -> tuple[int, int]:
        plan_id = self.repo.create_plan(owner, {"contentTitle": title, "week": 2, "session": 1, "course": course})
        version_id, _ = self.repo.insert_version_or_existing(
            plan_id, 1, content, plan_hash or f"hash-{title}", f"report-{title}", 1, "1.0", "1.0.0"
        )
        self.repo.set_current_version(plan_id, version_id)
        return plan_id, version_id

    def _review(self, version_id: int, status: str, findings: list | None = None, *, plan_hash: str) -> None:
        report = make_report(plan_hash, status=status, findings=findings)
        payload = json.dumps(report, ensure_ascii=False)
        review_id = self.repo.insert_review(version_id, 1, payload, "sha-" + status, status, "native_subagent")
        if findings:
            self.repo.insert_findings(review_id, findings)

    def _seed(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        valid_content = json.dumps(plan, ensure_ascii=False)
        valid_hash = engine.plan_hash(plan)

        plan_a, version_a = self._plan(self.teacher1, "通过课", content=valid_content, plan_hash=valid_hash)
        self._review(version_a, "passed", plan_hash=valid_hash)
        job_id = self.repo.create_export_job(version_a, "1.0.0", self.teacher1, "pending")
        self.repo.update_export_job(job_id, "succeeded", f"exports/{job_id}.docx", "docx-sha")

        blocker = {"id": "AR-1", "severity": "blocker", "status": "open"}
        plan_b, version_b = self._plan(self.teacher1, "退回课", content=valid_content, plan_hash="hash-退回课")
        self._review(version_b, "needs_repair", [blocker], plan_hash="hash-退回课")

        plan_c, version_c = self._plan(self.teacher1, "结构失败课")
        self._review(version_c, "passed", plan_hash="hash-结构失败课")

        plan_d, version_d = self._plan(self.teacher1, "已删课", content=valid_content, plan_hash="hash-已删课")
        self._review(version_d, "passed", plan_hash="hash-已删课")
        self.repo.soft_delete_plan(plan_d)

        plan_e, version_e = self._plan(self.teacher2, "英语课", "英语", content=valid_content, plan_hash="hash-英语课")
        self._review(version_e, "passed", plan_hash="hash-英语课")

        self.repo.insert_sync_log("push", "pkg-1", valid_hash, "created", "", self.teacher1)
        self.repo.insert_sync_log("push", "pkg-2", "hash-x", "conflict", "CONFLICT_STALE", self.teacher1)
        self.repo.conn.execute(
            "INSERT INTO task (course, week, session, title, owner_id, status, created_at)"
            " VALUES ('信息技术', 2, 1, '任务A', ?, 'exported', datetime('now'))",
            (self.teacher1,),
        )

    def _login(self, username: str) -> None:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)

    def _metrics(self) -> dict[str, dict]:
        return {item["key"]: item for item in self.client.get("/api/v1/stats/summary").json()["metrics"]}

    def test_nine_metrics_with_numerator_and_denominator(self) -> None:
        self._login("admin1")
        body = self.client.get("/api/v1/stats/summary").json()
        self.assertEqual(body["scope"], "all")
        self.assertEqual(len(body["metrics"]), 9)
        metrics = {item["key"]: item for item in body["metrics"]}
        self.assertEqual((metrics["structure_rate"]["numerator"], metrics["structure_rate"]["denominator"]), (3, 4))
        self.assertEqual(metrics["structure_rate"]["value"], 0.75)
        self.assertEqual((metrics["defect_density"]["numerator"], metrics["defect_density"]["denominator"]), (1, 4))
        self.assertEqual(metrics["sync_consistency"]["value"], 0.5)
        self.assertEqual((metrics["task_completion"]["numerator"], metrics["task_completion"]["denominator"]), (1, 1))
        self.assertEqual(metrics["task_completion"]["value"], 1.0)
        self.assertEqual(metrics["gold_standard"]["value"], None)
        self.assertEqual(metrics["export_seconds"]["denominator"], 1)
        self.assertIn("filters", metrics["structure_rate"])

    def test_course_filter_applies_to_all_metrics(self) -> None:
        self._login("admin1")
        body = self.client.get("/api/v1/stats/summary?course=英语").json()
        metrics = {item["key"]: item for item in body["metrics"]}
        # 只有"英语课"命中：1 份教案
        self.assertEqual(metrics["structure_rate"]["denominator"], 1)
        # 导出与任务都属于"信息技术"，筛选后没有样本 → 必须不可用，不能返回全量数
        self.assertFalse(metrics["export_seconds"]["available"])
        self.assertEqual(metrics["export_seconds"]["denominator"], 0)
        self.assertFalse(metrics["task_completion"]["available"])
        self.assertEqual(metrics["task_completion"]["denominator"], 0)
        # sync_log 无教案维度，带筛选时明确不可用
        self.assertFalse(metrics["sync_consistency"]["available"])
        self.assertEqual(metrics["sync_consistency"]["denominator"], 0)

    def test_deleted_plan_excluded_everywhere(self) -> None:
        self._login("admin1")
        metrics = self._metrics()
        self.assertEqual(metrics["structure_rate"]["denominator"], 4)
        self.assertEqual(metrics["evidence_rate"]["denominator"], 4)
        self.assertEqual(metrics["defect_density"]["denominator"], 4)

    def test_scope_for_teacher_lead_admin(self) -> None:
        self._login("teacher1")
        own = self._metrics()
        self.assertEqual(own["structure_rate"]["denominator"], 3)
        self._login("lead1")
        group = self._metrics()
        self.assertEqual(group["structure_rate"]["denominator"], 3)
        self._login("admin1")
        self.assertEqual(self._metrics()["structure_rate"]["denominator"], 4)

    def test_empty_is_null_not_zero(self) -> None:
        self.repo.insert_user("teacher3", "新老师", "teacher", security.hash_password(PASSWORD), "计算机")
        self._login("teacher3")
        metrics = self._metrics()
        self.assertIsNone(metrics["structure_rate"]["value"])
        self.assertEqual(metrics["structure_rate"]["denominator"], 0)
        self.assertIsNone(metrics["task_completion"]["value"])

    def test_course_filter(self) -> None:
        self._login("admin1")
        filtered = self.client.get("/api/v1/stats/summary?course=英语").json()
        metrics = {item["key"]: item for item in filtered["metrics"]}
        self.assertEqual(metrics["structure_rate"]["denominator"], 1)
        self.assertEqual(filtered["filters"]["course"], "英语")

    def test_export_duration_unit_is_minutes(self) -> None:
        self._login("admin1")
        metrics = self._metrics()
        self.assertEqual(metrics["export_seconds"]["unit"], "分钟")
        self.assertEqual(metrics["export_seconds"]["denominator"], 1)
        self.assertIsNotNone(metrics["export_seconds"]["value"])

    def test_class_filter_limits_scope(self) -> None:
        self._login("admin1")
        filtered = self.client.get("/api/v1/stats/summary?class=计算机1班").json()
        metrics = {item["key"]: item for item in filtered["metrics"]}
        # setUp 里的教案都没有挂任务，按班级筛选后没有样本
        self.assertEqual(metrics["structure_rate"]["denominator"], 0)
        self.assertFalse(metrics["task_completion"]["available"])
        # 同步日志没有班级维度：带班级筛选时必须标不可用，不能回显筛选却给全量（R2-B1）
        self.assertFalse(metrics["sync_consistency"]["available"])
        self.assertIsNone(metrics["sync_consistency"]["value"])
        self.assertEqual(filtered["filters"]["class"], "计算机1班")

    def test_export_csv_lists_nine_metrics(self) -> None:
        self._login("admin1")
        response = self.client.get("/api/v1/stats/export.csv")
        self.assertEqual(response.status_code, 200, response.text)
        lines = [line for line in response.text.splitlines() if line]
        self.assertEqual(len(lines), 10)  # 表头 + 9 项指标
        self.assertTrue(lines[0].lstrip("\ufeff").startswith("key,label,numerator,denominator"))
        self.assertIn("structure_rate", response.text)


if __name__ == "__main__":
    unittest.main()
