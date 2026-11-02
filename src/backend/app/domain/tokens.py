# -*- coding: utf-8 -*-
"""HS256 JWT 的签发与校验：纯函数，不依赖 FastAPI / SQLite，便于单测。

只用标准库（hmac + hashlib + base64）实现，避免为一个基础能力引入第三方依赖；
签名比较用 hmac.compare_digest，避免时序侧信道。

解析失败不抛异常而是返回 (None, 原因)：调用方（application 层）据此映射 401，
这样 domain 里不需要异常分支，也符合闸门"只有一个错误适配层"的约定。
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from contextlib import suppress
from typing import Any

HEADER = {"alg": "HS256", "typ": "JWT"}
_REASONS = {
    "secret": "缺少 JWT 密钥",
    "format": "令牌格式错误",
    "signature": "签名不匹配",
    "decode": "令牌内容不可解析",
    "algorithm": "不支持的签名算法",
    "expired": "令牌已过期",
    "issued": "令牌签发时间异常",
    "claims": "令牌载荷字段不合法",
    "issuer": "令牌签发方不匹配",
}


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes | None:
    holder: dict[str, bytes] = {}
    with suppress(ValueError, TypeError, binascii.Error):
        holder["raw"] = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    return holder.get("raw")


def _loads(text: str) -> Any:
    holder: dict[str, Any] = {}
    with suppress(ValueError, TypeError):
        holder["value"] = json.loads(text)
    return holder.get("value")


def _sign(message: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message.encode("ascii"), hashlib.sha256).digest()
    return _b64encode(digest)


def issue(claims: dict[str, Any], secret: str, *, now: int | None = None) -> str:
    if not secret:
        raise ValueError(_REASONS["secret"])
    issued_at = int(now if now is not None else time.time())
    payload = {**claims, "iat": issued_at}
    header = _b64encode(json.dumps(HEADER, separators=(",", ":")).encode("utf-8"))
    body = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return f"{header}.{body}.{_sign(f'{header}.{body}', secret)}"


def decode(token: str, secret: str, *, now: int | None = None) -> tuple[dict[str, Any] | None, str]:
    """返回 (载荷, 空串) 或 (None, 失败原因)。"""
    if not secret:
        return None, _REASONS["secret"]
    parts = str(token or "").split(".")
    if len(parts) != 3:
        return None, _REASONS["format"]
    header, body, signature = parts
    if not (header.isascii() and body.isascii() and signature.isascii()):
        return None, _REASONS["format"]
    if not hmac.compare_digest(
        _sign(f"{header}.{body}", secret).encode("ascii"), signature.encode("ascii")
    ):
        return None, _REASONS["signature"]
    raw_header, raw_body = _b64decode(header), _b64decode(body)
    if raw_header is None or raw_body is None:
        return None, _REASONS["decode"]
    head, payload = _loads(raw_header.decode("utf-8", "replace")), _loads(raw_body.decode("utf-8", "replace"))
    if not isinstance(head, dict) or head.get("alg") != "HS256":
        return None, _REASONS["algorithm"]
    if not isinstance(payload, dict):
        return None, _REASONS["decode"]
    current = int(now if now is not None else time.time())
    subject = payload.get("sub")
    if not isinstance(subject, int) or isinstance(subject, bool) or subject <= 0:
        return None, _REASONS["claims"]
    version = payload.get("tv")
    if not isinstance(version, int) or isinstance(version, bool):
        return None, _REASONS["claims"]
    if payload.get("iss") != "lpp":
        return None, _REASONS["issuer"]
    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or isinstance(expires_at, bool):
        return None, _REASONS["claims"]
    if expires_at <= current:
        return None, _REASONS["expired"]
    issued_at = payload.get("iat")
    if not isinstance(issued_at, int) or isinstance(issued_at, bool):
        return None, _REASONS["claims"]
    if issued_at > current + 300:
        return None, _REASONS["issued"]
    return payload, ""
