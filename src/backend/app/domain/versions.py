# -*- coding: utf-8 -*-
"""版本白名单：与插件端常量、契约保持一致，由闸门 BC-06 校验。"""
from __future__ import annotations

from typing import Any

VERSIONS: dict[str, Any] = {
    "schemaVersion": 1,
    "rubricVersion": "1.0",
    "rulesVersion": "1.1.0",
    "engineVersion": "1.0.0",
}

SUPPORTED_SCHEMA_VERSIONS = {VERSIONS["schemaVersion"]}
SUPPORTED_RUBRIC_VERSIONS = {VERSIONS["rubricVersion"]}


def supported_versions() -> dict[str, list]:
    return {
        "schemaVersion": sorted(SUPPORTED_SCHEMA_VERSIONS),
        "rubricVersion": sorted(SUPPORTED_RUBRIC_VERSIONS),
    }


def is_supported(schema_version: Any, rubric_version: Any) -> bool:
    return (
        isinstance(schema_version, int)
        and schema_version in SUPPORTED_SCHEMA_VERSIONS
        and rubric_version in SUPPORTED_RUBRIC_VERSIONS
    )
