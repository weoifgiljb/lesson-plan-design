# -*- coding: utf-8 -*-
"""角色、锁定与 CSRF 规则。"""
from __future__ import annotations

import unittest

from app.domain import auth, roles


class TestRoles(unittest.TestCase):
    def test_role_set_and_labels(self) -> None:
        self.assertEqual(set(roles.ROLES), {"teacher", "lead", "admin"})
        for role in roles.ROLES:
            self.assertTrue(roles.is_valid_role(role))
            self.assertIn(role, roles.ROLE_LABELS)
        self.assertFalse(roles.is_valid_role("root"))

    def test_can_access_owner(self) -> None:
        self.assertTrue(roles.can_access_owner("teacher", 7, 7))
        self.assertFalse(roles.can_access_owner("teacher", 7, 8))
        self.assertTrue(roles.can_access_owner("admin", 7, 8))
        self.assertFalse(roles.can_access_owner("lead", 7, 8))

    def test_allowed(self) -> None:
        self.assertTrue(roles.allowed("lead", ("teacher", "lead")))
        self.assertFalse(roles.allowed("admin", ("teacher",)))


class TestAuthRules(unittest.TestCase):
    def test_failure_counter_and_lock(self) -> None:
        count, lock = auth.next_failure(0, 5)
        self.assertEqual((count, lock), (1, False))
        count, lock = auth.next_failure(4, 5)
        self.assertEqual((count, lock), (5, True))
        self.assertTrue(auth.should_lock(5, 5))
        self.assertFalse(auth.should_lock(4, 5))

    def test_csrf_matches(self) -> None:
        self.assertTrue(auth.csrf_matches("abc", "abc"))
        self.assertFalse(auth.csrf_matches("abc", "abd"))
        self.assertFalse(auth.csrf_matches("", ""))
        self.assertFalse(auth.csrf_matches(None, "abc"))  # type: ignore[arg-type]

    def test_reason_length(self) -> None:
        self.assertTrue(auth.reason_is_shorter("太短"))
        self.assertFalse(auth.reason_is_shorter("这是足够长的理由"))


if __name__ == "__main__":
    unittest.main()
