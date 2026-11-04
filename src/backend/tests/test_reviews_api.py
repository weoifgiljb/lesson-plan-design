# -*- coding: utf-8 -*-
"""审查中心 API：六种状态、证据链缺项、范围权限与时间筛选。"""
from __future__ import annotations

import hashlib
import json
import unittest

from fastapi.testclient import TestClient

from support import isolated_data_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


def make_report(
    plan_hash: str,
    round_number: int = 1,
    *,
    status: str = "passed",
    findings: list | None = None,
    overrides: list | None = None,
    mode: str = "native_subagent",
    structural_ok: bool = True,
    attestation: str | None = "no_counterexample",
) -> dict:
    return {
        "schemaVersion": 1,
        "rubricVersion": "1.0",
        "toolVersion": "1.0.0",
        "planHash": plan_hash,
        "planSnapshot": None,
        "round": round_number,
        "duplicateReview": False,
        "reviewer": mode,
        "independence": mode,
        "reviewedAt": "2026-10-27T00:00:00+00:00",
        "structuralValidation": {"ok": structural_ok},
        "findings": findings or [],
        "overrides": overrides or [],
        "repairHistory": [],
        "attestation": attestation,
        "status": status,
        "conclusion": "",
    }


class TestReviewsApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.connection = open_database(self.root / "app.db")
        self.repo = Repo(self.connection)
        self.teacher1 = self.repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD), "计算机")
        self.teacher2 = self.repo.insert_user("teacher2", "李老师", "teacher", security.hash_password(PASSWORD), "英语")
        self.lead1 = self.repo.insert_user("lead1", "王组长", "lead", security.hash_password(PASSWORD), "计算机")
        self.admin = self.repo.insert_user("admin1", "管理员", "admin", security.hash_password(PASSWORD), "")
        self.reviews = {}
        self._seed()
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.connection.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _plan(self, owner: int, title: str) -> tuple[int, int]:
        plan_id = self.repo.create_plan(
            owner, {"contentTitle": title, "week": 2, "session": 1, "course": "信息技术"}
        )
        version_id, _ = self.repo.insert_version_or_existing(
            plan_id, 1, "{}", f"hash-{title}", f"report-{title}", 1, "1.0", "1.0.0"
        )
        return plan_id, version_id

    def _review(
        self,
        plan_id: int,
        version_id: int,
        report: dict,
        *,
        round_number: int = 1,
        severity: str | None = None,
    ) -> int:
        review_id = self.repo.insert_review(
            version_id,
            round_number,
            json.dumps(report, ensure_ascii=False),
            hashlib.sha256(json.dumps(report, ensure_ascii=False).encode("utf-8")).hexdigest(),
            report["status"],
            report.get("independence") or report.get("reviewer") or "role_simulation",
        )
        if severity:
            self.repo.insert_findings(
                review_id, [{"id": f"AR-{review_id}", "severity": severity, "status": "open", "hypothesis": "x"}]
            )
        return review_id

    def _seed(self) -> None:
        plan_a, version_a = self._plan(self.teacher1, "通过课")
        self.reviews["passed"] = self._review(plan_a, version_a, make_report("hash-通过课"))

        blocker = {"id": "AR-B", "severity": "blocker", "status": "open"}
        plan_b, version_b = self._plan(self.teacher1, "待修复课")
        report_b = make_report("hash-待修复课", status="needs_repair", findings=[blocker], attestation=None)
        self.reviews["needs_repair"] = self._review(plan_b, version_b, report_b, severity="blocker")

        plan_c, version_c1 = self._plan(self.teacher1, "跳号课")
        version_c3, _ = self.repo.insert_version_or_existing(
            plan_c, 3, "{}", "hash-跳号课-v3", "report-跳号课-v3", 1, "1.0", "1.0.0"
        )
        self._review(plan_c, version_c1, make_report("hash-跳号课"))
        self.reviews["round_gap"] = self._review(plan_c, version_c3, make_report("hash-跳号课-v3", 3), round_number=3)

        waived = {"id": "AR-W", "severity": "major", "status": "waived"}
        plan_d, version_d = self._plan(self.teacher1, "缺放行课")
        report_d = make_report("hash-缺放行课", status="passed_with_override", findings=[waived])
        self.reviews["missing_override"] = self._review(plan_d, version_d, report_d, severity="major")

        plan_e, version_e = self._plan(self.teacher1, "结构失败课")
        report_e = make_report("hash-结构失败课", status="structure_invalid", structural_ok=False, attestation=None)
        self.reviews["structure_invalid"] = self._review(plan_e, version_e, report_e)

        plan_f, version_f = self._plan(self.teacher1, "待审课")
        report_f = make_report("hash-待审课", status="pending_reviewer", attestation=None)
        self.reviews["pending_reviewer"] = self._review(plan_f, version_f, report_f)

        accepted = {"id": "AR-M", "severity": "minor", "status": "accepted"}
        override = {
            "findingId": "AR-M",
            "planHash": "hash-接受课",
            "teacher": "张老师",
            "reason": "下次修订一并处理",
            "kind": "minor_acceptance",
        }
        plan_g, version_g = self._plan(self.teacher1, "接受课")
        report_g = make_report(
            "hash-接受课", status="passed_with_accepted_minor", findings=[accepted], overrides=[override]
        )
        self.reviews["accepted_minor"] = self._review(plan_g, version_g, report_g)

        plan_h, version_h = self._plan(self.teacher1, "哈希不符课")
        self.reviews["hash_mismatch"] = self._review(plan_h, version_h, make_report("other-hash"))

        plan_i, version_i = self._plan(self.teacher2, "英语课")
        self.reviews["other_group"] = self._review(plan_i, version_i, make_report("hash-英语课"))

    def _login(self, username: str) -> None:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)

    def test_list_scope_and_filters(self) -> None:
        self._login("teacher1")
        listing = self.client.get("/api/v1/reviews").json()
        self.assertEqual(listing["total"], 9)
        self._login("lead1")
        self.assertEqual(self.client.get("/api/v1/reviews").json()["total"], 9)
        self._login("teacher2")
        self.assertEqual(self.client.get("/api/v1/reviews").json()["total"], 1)

        self._login("teacher1")
        passed = self.client.get("/api/v1/reviews?status=passed").json()
        self.assertTrue(passed["items"])
        self.assertTrue(all(item['status'] == 'passed' for item in passed['items']))
        blocker = self.client.get("/api/v1/reviews?severity=blocker").json()
        self.assertEqual(blocker["items"][0]["reviewId"], self.reviews["needs_repair"])
        by_teacher = self.client.get("/api/v1/reviews?teacher=张老师").json()
        self.assertEqual(by_teacher["total"], 9)
        paged = self.client.get("/api/v1/reviews?page=2&pageSize=3").json()
        self.assertEqual((paged["page"], len(paged["items"]), paged["total"]), (2, 3, 9))

    def test_list_marks_evidence_gaps(self) -> None:
        self._login("teacher1")
        items = {item["reviewId"]: item for item in self.client.get("/api/v1/reviews").json()["items"]}
        self.assertIn("round_continuous", items[self.reviews["round_gap"]]["evidence"]["gaps"])
        self.assertIn("overrides_complete", items[self.reviews["missing_override"]]["evidence"]["gaps"])
        self.assertIn("hash_match", items[self.reviews["hash_mismatch"]]["evidence"]["gaps"])
        self.assertTrue(items[self.reviews["passed"]]["evidence"]["complete"])

    def test_detail_shows_five_items_and_report(self) -> None:
        self._login("teacher1")
        detail = self.client.get(f"/api/v1/reviews/{self.reviews['passed']}").json()
        self.assertEqual(len(detail["evidence"]["items"]), 5)
        self.assertTrue(detail["evidence"]["complete"])
        self.assertEqual(detail["report"]["status"], "passed")
        self.assertEqual(detail["review"]["contentTitle"], "通过课")
        # R4-15：repairHistory 与 review 的课程/周次/课次要进模型，不能只靠 extra=allow 透传
        self.assertIsInstance(detail["repairHistory"], list)
        self.assertEqual(detail["review"]["course"], "信息技术")
        self.assertEqual((detail["review"]["week"], detail["review"]["session"]), (2, 1))
        gap = self.client.get(f"/api/v1/reviews/{self.reviews['round_gap']}").json()
        item = next(entry for entry in gap["evidence"]["items"] if entry["key"] == "round_continuous")
        self.assertFalse(item["ok"])
        self.assertIn("轮次不连续", item["reason"])

    def test_date_filter_boundary(self) -> None:
        # 固定全部审查的入库时间：本地日（+08:00）为准，且不依赖运行当天
        # 其余 8 条 = 本地 2026-10-30 12:00；边界条 = 本地 2026-10-29 23:59:59
        self.connection.execute("UPDATE review SET created_at = '2026-10-30T04:00:00+00:00'")
        self.connection.execute(
            "UPDATE review SET created_at = '2026-10-29T15:59:59+00:00' WHERE id = ?",
            (self.reviews["passed"],),
        )
        self.connection.commit()
        self._login("teacher1")
        same_day = self.client.get("/api/v1/reviews?dateFrom=2026-10-29&dateTo=2026-10-29").json()
        self.assertEqual([item["reviewId"] for item in same_day["items"]], [self.reviews["passed"]])
        next_day = self.client.get("/api/v1/reviews?dateFrom=2026-10-30&dateTo=2026-10-30").json()
        self.assertNotIn(self.reviews["passed"], [item["reviewId"] for item in next_day["items"]])
        self.assertGreater(next_day["total"], 0)

    def test_date_filter_uses_local_day_not_utc_day(self) -> None:
        # UTC 2026-10-29T16:00 = 本地 2026-10-30 00:00；按本地日必须落在 10-30
        self.connection.execute(
            "UPDATE review SET created_at = '2026-10-29T16:00:00+00:00' WHERE id = ?",
            (self.reviews["passed"],),
        )
        self.connection.commit()
        self._login("teacher1")
        on_29 = self.client.get("/api/v1/reviews?dateFrom=2026-10-29&dateTo=2026-10-29").json()
        self.assertNotIn(self.reviews["passed"], [item["reviewId"] for item in on_29["items"]])
        on_30 = self.client.get("/api/v1/reviews?dateFrom=2026-10-30&dateTo=2026-10-30").json()
        self.assertIn(self.reviews["passed"], [item["reviewId"] for item in on_30["items"]])

    def test_bad_report_is_marked_not_500(self) -> None:
        # 坏 JSON：整页仍 200，该行 evidence.gaps 标 report_unreadable（证据链最需要它的时候不能 500）
        self.connection.execute(
            "UPDATE review SET report_json = '{not json' WHERE id = ?", (self.reviews["passed"],)
        )
        self.connection.commit()
        self._login("teacher1")
        listing = self.client.get("/api/v1/reviews")
        self.assertEqual(listing.status_code, 200, listing.text)
        items = {item["reviewId"]: item for item in listing.json()["items"]}
        self.assertIn("report_unreadable", items[self.reviews["passed"]]["evidence"]["gaps"])
        detail = self.client.get(f"/api/v1/reviews/{self.reviews['passed']}")
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertIn("report_unreadable", detail.json()["evidence"]["gaps"])

    def test_bad_field_types_are_marked_not_500(self) -> None:
        # severity/status 写成对象：类型守卫应标红而不是抛 TypeError
        report = {
            "schemaVersion": 1,
            "rubricVersion": "1.0",
            "toolVersion": "1.0.0",
            "planHash": "hash",
            "round": 1,
            "reviewer": "张老师",
            "independence": {},
            "reviewedAt": "2026-10-28T00:00:00+00:00",
            "structuralValidation": {"ok": True},
            "findings": [{"id": "AR-1", "severity": {}, "status": {"x": 1}}],
            "overrides": [],
            "repairHistory": [],
            "attestation": "no_counterexample",
            "status": {},
            "conclusion": "",
        }
        self.connection.execute(
            "UPDATE review SET report_json = ? WHERE id = ?",
            (json.dumps(report, ensure_ascii=False), self.reviews["passed"]),
        )
        self.connection.commit()
        self._login("teacher1")
        listing = self.client.get("/api/v1/reviews")
        self.assertEqual(listing.status_code, 200, listing.text)
        items = {item["reviewId"]: item for item in listing.json()["items"]}
        self.assertFalse(items[self.reviews["passed"]]["evidence"]["complete"])

    def test_lead_cannot_read_other_group_detail(self) -> None:
        self._login("lead1")
        self.assertEqual(self.client.get(f"/api/v1/reviews/{self.reviews['passed']}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/reviews/{self.reviews['other_group']}").status_code, 403)

    def test_detail_permissions(self) -> None:
        self._login("teacher2")
        self.assertEqual(self.client.get(f"/api/v1/reviews/{self.reviews['passed']}").status_code, 403)
        self._login("lead1")
        self.assertEqual(self.client.get(f"/api/v1/reviews/{self.reviews['passed']}").status_code, 200)
        self._login("admin1")
        self.assertEqual(self.client.get(f"/api/v1/reviews/{self.reviews['passed']}").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/reviews").status_code, 403)

    def test_no_mutation_endpoint(self) -> None:
        self._login("teacher1")
        self.assertEqual(self.client.post(f"/api/v1/reviews/{self.reviews['passed']}").status_code, 405)


if __name__ == "__main__":
    unittest.main()
