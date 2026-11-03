# -*- coding: utf-8 -*-
"""教案库 API：范围过滤、详情、版本链、差异与软删除。"""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from factories import build_package
from support import isolated_data_dir, load_json_bytes, plugin_report, read_package_dir, tempdir

from app.adapters.db.connection import open_database
from app.adapters.db.repo import Repo
from app.application import ingest_service
from app.domain import security
from app.main import create_app

PASSWORD = "Lesson2026"


class TestPlansApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempdir()
        self.root = self._tmp.__enter__()
        self._env = isolated_data_dir(self.root)
        self._env.__enter__()
        self.db_file = self.root / "app.db"
        self.connection = open_database(self.db_file)
        self.repo = Repo(self.connection)
        self.teacher1 = self.repo.insert_user("teacher1", "张老师", "teacher", security.hash_password(PASSWORD), "计算机")
        self.teacher2 = self.repo.insert_user("teacher2", "李老师", "teacher", security.hash_password(PASSWORD), "英语")
        self.lead1 = self.repo.insert_user("lead1", "王组长", "lead", security.hash_password(PASSWORD), "计算机")
        self.admin = self.repo.insert_user("admin1", "管理员", "admin", security.hash_password(PASSWORD), "")
        self.plan1 = self._import(self.teacher1, read_package_dir("valid-package"))
        self.plan2 = self._import(self.teacher2, read_package_dir("valid-package"))
        self._import_second_version()
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.connection.close()
        self._env.__exit__(None, None, None)
        self._tmp.__exit__(None, None, None)

    def _import(self, owner_id: int, files: dict[str, bytes]) -> int:
        return ingest_service.import_package(self.repo, files=files, owner_id=owner_id).plan_id

    def _import_second_version(self) -> None:
        files = read_package_dir("valid-package")
        plan = load_json_bytes(files["plan.json"])
        previous = load_json_bytes(files["plan.review.json"])
        plan["activityFlow"]["summary"] = "第二次修订后的课堂小结"
        report = plugin_report(plan, round_number=2, previous_report=previous)
        ingest_service.import_package(
            self.repo, files=build_package(plan, report=report), owner_id=self.teacher1
        )

    def _login(self, username: str) -> str:
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["csrfToken"]

    def _get(self, path: str):
        return self.client.get(path)

    def test_list_respects_role_scope(self) -> None:
        self._login("teacher1")
        own = self._get("/api/v1/plans")
        self.assertEqual(own.status_code, 200, own.text)
        self.assertEqual(own.json()["total"], 1)
        self.assertEqual(own.json()["items"][0]["planId"], self.plan1)
        self._login("lead1")
        group = self._get("/api/v1/plans")
        self.assertEqual([item["planId"] for item in group.json()["items"]], [self.plan1])
        self._login("admin1")
        everything = self._get("/api/v1/plans")
        self.assertEqual(everything.json()["total"], 2)

    def test_list_filters_and_pagination(self) -> None:
        self._login("admin1")
        self.assertEqual(self._get("/api/v1/plans?week=2").json()["total"], 2)
        self.assertEqual(self._get("/api/v1/plans?week=9").json()["total"], 0)
        self.assertEqual(self._get("/api/v1/plans?teacher=张老师").json()["total"], 1)
        by_status = self._get("/api/v1/plans?status=passed").json()
        self.assertEqual(by_status["total"], 2)
        # 非法审查状态必须 422，不能静默返回空列表（与 tasks/reviews/users 同口径）
        self.assertEqual(self._get("/api/v1/plans?status=bogus").status_code, 422)
        paged = self._get("/api/v1/plans?page=2&pageSize=1").json()
        self.assertEqual((paged["page"], paged["pageSize"], paged["total"], len(paged["items"])), (2, 1, 2, 1))

    def test_detail_returns_content_and_permissions(self) -> None:
        self._login("teacher1")
        own = self._get(f"/api/v1/plans/{self.plan1}")
        self.assertEqual(own.status_code, 200, own.text)
        body = own.json()
        self.assertEqual(body["plan"]["contentTitle"], "一级考证辅导2")
        self.assertEqual(body["currentVersion"]["versionNo"], 2)
        self.assertIn("activityFlow", body["currentVersion"]["content"])
        self.assertEqual(body["latestReview"]["status"], "passed")
        self._login("teacher2")
        self.assertEqual(self._get(f"/api/v1/plans/{self.plan1}").status_code, 403)
        self.assertEqual(self._get("/api/v1/plans/9999").status_code, 404)

    def test_versions_and_diff(self) -> None:
        self._login("teacher1")
        versions = self._get(f"/api/v1/plans/{self.plan1}/versions").json()
        self.assertEqual([item["versionNo"] for item in versions["items"]], [1, 2])
        self.assertEqual(versions["items"][1]["status"], "passed")
        diff = self._get(f"/api/v1/plans/{self.plan1}/diff").json()
        self.assertEqual((diff["fromVersion"], diff["toVersion"]), (1, 2))
        paths = {item["path"] for item in diff["changes"]}
        self.assertIn("activityFlow.summary", paths)
        explicit = self._get(f"/api/v1/plans/{self.plan1}/diff?fromVersion=1&toVersion=2").json()
        self.assertEqual(explicit["count"], diff["count"])

    def test_soft_delete_is_idempotent_and_audited(self) -> None:
        self._login("teacher2")
        csrf = self.client.cookies.get("lpp_csrf")
        denied = self.client.delete(f"/api/v1/plans/{self.plan1}", headers={"X-CSRF-Token": csrf})
        self.assertEqual(denied.status_code, 403, denied.text)
        self._login("teacher1")
        csrf = self.client.cookies.get("lpp_csrf")
        first = self.client.delete(f"/api/v1/plans/{self.plan1}", headers={"X-CSRF-Token": csrf})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertFalse(first.json()["alreadyDeleted"])
        self.assertEqual(self._get(f"/api/v1/plans/{self.plan1}").status_code, 404)
        second = self.client.delete(f"/api/v1/plans/{self.plan1}", headers={"X-CSRF-Token": csrf})
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["alreadyDeleted"])
        actions = [row["action"] for row in self.repo.list_audit(50)]
        self.assertEqual(actions.count("plan.delete"), 1)
        self.assertIn("plan.delete.denied", actions)

    def test_lead_can_delete_own_plan(self) -> None:
        own_plan = self._import(self.lead1, read_package_dir("valid-package"))
        self._login("lead1")
        csrf = self.client.cookies.get("lpp_csrf")
        response = self.client.delete(f"/api/v1/plans/{own_plan}", headers={"X-CSRF-Token": csrf})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["alreadyDeleted"])

    def test_lead_cannot_read_other_group(self) -> None:
        self._login("lead1")
        for path in (
            f"/api/v1/plans/{self.plan2}",
            f"/api/v1/plans/{self.plan2}/versions",
            f"/api/v1/plans/{self.plan2}/diff",
        ):
            with self.subTest(path=path):
                self.assertEqual(self._get(path).status_code, 403)
        audit = [row for row in self.repo.list_audit(100) if row["action"] == "plan.read.denied"]
        self.assertGreaterEqual(len(audit), 3)

    def test_diff_boundaries(self) -> None:
        plan = load_json_bytes(read_package_dir("valid-package")["plan.json"])
        plan["contentTitle"] = "单版本课题"
        single_plan = self._import(self.teacher1, build_package(plan, report=plugin_report(plan)))
        self._login("teacher1")
        single = self._get(f"/api/v1/plans/{single_plan}/diff")
        self.assertEqual(single.status_code, 404)
        self.assertIn("两个版本", single.json()["message"])

        missing = self._get(f"/api/v1/plans/{self.plan1}/diff?fromVersion=999")
        self.assertEqual(missing.status_code, 404)
        same = self._get(f"/api/v1/plans/{self.plan1}/diff?fromVersion=1&toVersion=1")
        self.assertEqual(same.status_code, 404)
        self.assertIn("相同", same.json()["message"])
        zero = self._get(f"/api/v1/plans/{self.plan1}/diff?fromVersion=0")
        self.assertEqual(zero.status_code, 404)

    def test_deleted_plan_hidden_everywhere(self) -> None:
        self._login("teacher1")
        csrf = self.client.cookies.get("lpp_csrf")
        self.client.delete(f"/api/v1/plans/{self.plan1}", headers={"X-CSRF-Token": csrf})
        self.assertEqual(self._get("/api/v1/plans").json()["total"], 0)
        self.assertEqual(self._get(f"/api/v1/plans/{self.plan1}/versions").status_code, 404)
        self.assertEqual(self._get(f"/api/v1/plans/{self.plan1}/diff").status_code, 404)
        self._login("admin1")
        admin_list = self._get("/api/v1/plans").json()
        self.assertEqual([item["planId"] for item in admin_list["items"]], [self.plan2])

    def test_admin_can_delete_others(self) -> None:
        self._login("admin1")
        csrf = self.client.cookies.get("lpp_csrf")
        response = self.client.delete(f"/api/v1/plans/{self.plan2}", headers={"X-CSRF-Token": csrf})
        self.assertEqual(response.status_code, 200, response.text)


if __name__ == "__main__":
    unittest.main()
