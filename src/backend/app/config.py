# -*- coding: utf-8 -*-
"""平台端配置：路径、上限、会话参数。所有值可被环境变量覆盖，便于测试与部署。"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "data"

MAX_PACKAGE_BYTES = 50 * 1024 * 1024
MAX_PACKAGE_FILES = 200
MAX_SAMPLE_BYTES = 2 * 1024 * 1024
ALLOWED_PACKAGE_SUFFIXES = (".json", ".png", ".jpg", ".jpeg", ".docx")
MANIFEST_NAME = "manifest.json"
PLAN_NAME = "plan.json"
REPORT_NAME = "plan.review.json"

SESSION_COOKIE = "lpp_session"
CSRF_COOKIE = "lpp_csrf"
CSRF_HEADER = "X-CSRF-Token"
SESSION_TTL_HOURS = 8
LOGIN_MAX_FAILURES = 5
LOGIN_LOCK_MINUTES = 10
MIN_PASSWORD_LENGTH = 8

JWT_TTL_MINUTES = 120
JWT_DEV_SECRET = "lpp-dev-secret-change-me"
ALLOW_REGISTRATION = True


def data_dir() -> Path:
    return Path(os.environ.get("LPP_DATA_DIR", str(DEFAULT_DATA_DIR))).resolve()


def db_path() -> Path:
    return data_dir() / "app.db"


def files_dir() -> Path:
    return data_dir() / "files"


def exports_dir() -> Path:
    return data_dir() / "exports"


def max_package_bytes() -> int:
    return int(os.environ.get("LPP_MAX_PACKAGE_BYTES", MAX_PACKAGE_BYTES))


def max_sample_bytes() -> int:
    return int(os.environ.get("LPP_MAX_SAMPLE_BYTES", MAX_SAMPLE_BYTES))


def cookie_secure() -> bool:
    return os.environ.get("LPP_COOKIE_SECURE", "0") == "1"


def session_ttl_hours() -> int:
    return int(os.environ.get("LPP_SESSION_TTL_HOURS", SESSION_TTL_HOURS))


def jwt_secret() -> str:
    return os.environ.get("LPP_JWT_SECRET", JWT_DEV_SECRET)


def jwt_ttl_minutes() -> int:
    return int(os.environ.get("LPP_JWT_TTL_MINUTES", JWT_TTL_MINUTES))


def allow_registration() -> bool:
    return os.environ.get("LPP_ALLOW_REGISTRATION", "1" if ALLOW_REGISTRATION else "0") == "1"
