# -*- coding: utf-8 -*-
"""入库复校：按固定顺序给出结论，平台独立重算，不采信包内自述。"""
from __future__ import annotations

from typing import Any

from app.domain import manifest as manifest_rules
from app.domain import report_rules, versions
from app.domain.verdict import PASS, Verdict, fail


def evaluate(
    *,
    manifest: dict[str, Any],
    files: dict[str, bytes],
    plan: dict[str, Any],
    report: dict[str, Any],
    report_sha256: str,
    plan_hash: str,
    snapshot_hash: str | None,
    previous_round: int,
    validation: dict[str, Any],
) -> Verdict:
    problem = _check_versions(manifest, report)
    if problem is not None:
        return problem
    if manifest.get("planHash") != plan_hash:
        return fail("HASH_MISMATCH", "教案内容哈希与 manifest 声明不一致", {"declared": manifest.get("planHash")})
    problem = manifest_rules.verify_files(manifest, files)
    if problem is not None:
        return problem
    if manifest.get("reportHash") != report_sha256:
        return fail("REPORT_INCONSISTENT", "审查报告哈希与 manifest 声明不一致")
    if validation.get("ok") is not True:
        return fail(
            "STRUCTURE_INVALID",
            "教案未通过结构校验",
            {"issues": validation.get("issues", []), "ruleVersion": validation.get("ruleVersion", "")},
        )
    problem = report_rules.check(
        report,
        plan_hash=plan_hash,
        snapshot_hash=snapshot_hash,
        structural_ok=True,
        previous_round=previous_round,
    )
    return problem if problem is not None else PASS


def _check_versions(manifest: dict[str, Any], report: dict[str, Any]) -> Verdict | None:
    if not versions.contract_supported(manifest.get("contractVersion")):
        return fail("SCHEMA_UNSUPPORTED", "契约包版本不受支持", versions.supported_versions())
    if not versions.is_supported(manifest.get("schemaVersion"), manifest.get("rubricVersion")):
        return fail("SCHEMA_UNSUPPORTED", "契约包版本不受支持", versions.supported_versions())
    if not versions.is_supported(report.get("schemaVersion"), report.get("rubricVersion")):
        return fail("SCHEMA_UNSUPPORTED", "审查报告版本不受支持", versions.supported_versions())
    return None
