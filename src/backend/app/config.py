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
REGISTER_MAX_PER_HOUR = 10
MIN_JWT_SECRET_LENGTH = 32


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


def dev_secret_allowed() -> bool:
    """只有显式声明 `LPP_ALLOW_DEV_SECRET=1`（本地开发/测试）才允许用内置密钥。"""
    return os.environ.get("LPP_ALLOW_DEV_SECRET", "0") == "1"


def strict_config() -> bool:
    """生产/联调（LPP_ENV=prod）或显式 LPP_STRICT_CONFIG=1 时，配置不合格直接拒绝启动。"""
    return os.environ.get("LPP_STRICT_CONFIG", "0") == "1" or os.environ.get(
        "LPP_ENV", "dev"
    ).lower() in {"prod", "production"}


def security_config_problems() -> list[str]:
    """启动自检：返回不可接受的配置问题，调用方据此拒绝启动或让 /health 报 degraded。"""
    problems: list[str] = []
    secret = jwt_secret()
    if secret == JWT_DEV_SECRET and not dev_secret_allowed():
        problems.append(
            "LPP_JWT_SECRET 仍为内置开发密钥：生产/联调必须设置独立密钥（或显式 LPP_ALLOW_DEV_SECRET=1）"
        )
    if len(secret) < MIN_JWT_SECRET_LENGTH:
        problems.append(f"LPP_JWT_SECRET 长度不足 {MIN_JWT_SECRET_LENGTH} 字节")
    raw_ttl = str(os.environ.get("LPP_JWT_TTL_MINUTES", JWT_TTL_MINUTES)).strip()
    if not raw_ttl.lstrip("-").isdigit():
        problems.append("LPP_JWT_TTL_MINUTES 不是整数")
    elif not 0 < int(raw_ttl) <= 24 * 60:
        problems.append("LPP_JWT_TTL_MINUTES 必须在 1 到 1440 分钟之间")
    return problems


def jwt_ttl_minutes() -> int:
    return int(os.environ.get("LPP_JWT_TTL_MINUTES", JWT_TTL_MINUTES))


def allow_registration() -> bool:
    return os.environ.get("LPP_ALLOW_REGISTRATION", "1" if ALLOW_REGISTRATION else "0") == "1"


def register_max_per_hour() -> int:
    return int(os.environ.get("LPP_REGISTER_MAX_PER_HOUR", REGISTER_MAX_PER_HOUR))
