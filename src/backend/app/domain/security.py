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


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$") if isinstance(stored, str) else []
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    _, n, r, p, salt_hex, digest_hex = parts
    if not (n.isdigit() and r.isdigit() and p.isdigit()):
        return False
    if len(salt_hex) % 2 or any(ch not in "0123456789abcdef" for ch in salt_hex.lower()):
        return False
    if any(ch not in "0123456789abcdef" for ch in digest_hex.lower()):
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
