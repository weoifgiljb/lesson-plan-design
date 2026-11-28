# -*- coding: utf-8 -*-
"""口令哈希、随机令牌与口令强度：纯函数，不读写数据库。"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from app.config import MIN_PASSWORD_LENGTH

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
TOKEN_BYTES = 32


def hash_password(password: str, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=actual_salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${actual_salt.hex()}${digest.hex()}"


def _hex_ok(value: str, *, min_len: int, max_len: int) -> bool:
    """hex 串长度/字符白名单：坏数据一律 False，不让 scrypt 抛 ValueError。"""
    if not isinstance(value, str) or len(value) % 2:
        return False
    if not min_len <= len(value) <= max_len:
        return False
    return all(ch in "0123456789abcdef" for ch in value.lower())


def _scrypt_params_ok(n: int, r: int, p: int) -> bool:
    """参数范围 + n 必须是 2 的幂；越界值会让 hashlib.scrypt 抛 ValueError。"""
    return (
        2**10 <= n <= 2**20
        and n & (n - 1) == 0
        and 1 <= r <= 32
        and 1 <= p <= 16
    )


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$") if isinstance(stored, str) else []
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    _, n, r, p, salt_hex, digest_hex = parts
    if not (n.isdigit() and r.isdigit() and p.isdigit()):
        return False
    if not _hex_ok(salt_hex, min_len=16, max_len=128):
        return False
    if not _hex_ok(digest_hex, min_len=16, max_len=256):
        return False
    if not _scrypt_params_ok(int(n), int(r), int(p)):
        return False
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt_hex),
        n=int(n),
        r=int(r),
        p=int(p),
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def password_problem(password: str) -> str | None:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        return f"口令至少 {MIN_PASSWORD_LENGTH} 位"
    if not any(char.isalpha() for char in password):
        return "口令必须包含字母"
    if not any(char.isdigit() for char in password):
        return "口令必须包含数字"
    return None


def new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_csrf_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)
