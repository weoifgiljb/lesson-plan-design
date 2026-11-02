# -*- coding: utf-8 -*-
"""会话编排：签发、解析与撤销。"""
from __future__ import annotations

from typing import Any

from app.adapters import clock
from app.adapters.db.repo import Repo
from app.config import session_ttl_hours
from app.domain import security


def create(repo: Repo, user_id: int) -> tuple[str, str]:
    token = security.new_token()
    csrf_token = security.new_csrf_token()
    repo.insert_session(user_id, security.token_hash(token), csrf_token, clock.iso_after(session_ttl_hours()))
    return token, csrf_token


def resolve(repo: Repo, token: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not token:
        return None
    session = repo.session_by_token_hash(security.token_hash(token))
    if session is None or clock.is_past(str(session.get("expires_at") or "")):
        return None
    user = repo.user_by_id(int(session["user_id"]))
    if user is None or not user.get("active"):
        return None
    return session, user


def revoke(repo: Repo, session_id: int) -> None:
    repo.revoke_session(int(session_id))
