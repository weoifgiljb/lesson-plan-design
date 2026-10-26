# -*- coding: utf-8 -*-
"""复校结论值对象：domain 只返回结论，不抛异常、不拼 HTTP 状态。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Verdict:
    ok: bool
    code: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


PASS = Verdict(ok=True)


def fail(code: str, message: str, details: dict[str, Any] | None = None) -> Verdict:
    return Verdict(ok=False, code=code, message=message, details=details or {})
