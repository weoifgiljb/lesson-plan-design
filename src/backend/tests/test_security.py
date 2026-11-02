# -*- coding: utf-8 -*-
"""口令哈希、强度与令牌。"""
from __future__ import annotations

import unittest

from app.domain import security


class TestSecurity(unittest.TestCase):
    def test_password_roundtrip(self) -> None:
        stored = security.hash_password("Lesson2026")
        self.assertTrue(stored.startswith("scrypt$"))
        self.assertTrue(security.verify_password("Lesson2026", stored))
        self.assertFalse(security.verify_password("lesson2026", stored))

    def test_salt_is_random(self) -> None:
        first = security.hash_password("Lesson2026")
        second = security.hash_password("Lesson2026")
        self.assertNotEqual(first, second)

    def test_password_strength(self) -> None:
        self.assertIsNotNone(security.password_problem("short1"))
        self.assertIsNotNone(security.password_problem("onlyletters"))
        self.assertIsNotNone(security.password_problem("12345678"))
        self.assertIsNone(security.password_problem("Lesson2026"))

    def test_tokens_are_unique_and_hashed_stably(self) -> None:
        token = security.new_token()
        self.assertNotEqual(token, security.new_token())
        self.assertEqual(security.token_hash(token), security.token_hash(token))
        self.assertNotEqual(security.new_csrf_token(), security.new_csrf_token())

    def test_broken_hash_is_rejected(self) -> None:
        self.assertFalse(security.verify_password("x", "md5$abc"))
        self.assertFalse(security.verify_password("x", ""))


if __name__ == "__main__":
    unittest.main()
