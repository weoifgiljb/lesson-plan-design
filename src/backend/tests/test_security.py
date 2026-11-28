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

    def test_corrupt_hash_parameters_return_false_instead_of_raising(self) -> None:
        # 空 salt / n 非 2 次幂 / 越界参数会让 hashlib.scrypt 抛 ValueError；
        # 登录路径必须得到 False（401），不能变成 500。
        salt = "ab" * 16
        digest = "cd" * 32
        for stored in (
            f"scrypt$16384$8$1$${digest}",
            f"scrypt$3$8$1${salt}${digest}",
            f"scrypt$1073741824$8$1${salt}${digest}",
            f"scrypt$16384$8$0${salt}${digest}",
            f"scrypt$16384$8$1${salt}$",
        ):
            with self.subTest(stored=stored[:24]):
                self.assertFalse(security.verify_password("x", stored))


if __name__ == "__main__":
    unittest.main()
