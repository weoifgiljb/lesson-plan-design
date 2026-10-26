# -*- coding: utf-8 -*-
"""生成双端测试样例（插件端 JSON + 平台端契约包）。

用法：py -3 tests/fixtures/dual-end/build_fixtures.py
所有产物落在本目录，可重复生成；不修改仓库其他文件。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
SKILL_SCRIPTS = ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from lib import adversarial_review, dump, load_json, plan_hash, validate_plan  # noqa: E402

EXAMPLE = ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "examples" / "信息技术0201.json"
C_PLAN = ROOT / "output" / "c-language-plans" / "第1周第1次_认识C语言与Dev-C++开发环境.json"
PLUGIN_DIR = BASE / "plugin"
PLATFORM_DIR = BASE / "platform"
PACKAGE_DIR = PLATFORM_DIR / "packages"
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c63000100000500010d0a2db4"
    "0000000049454e44ae426082"
)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(data) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def metadata_plan() -> dict:
    plan = load_json(EXAMPLE)
    plan["teacher"] = "张老师"
    plan["teachingObject"] = "计算机2301"
    plan["planNumber"] = "IT-0201"
    plan["teachDate"] = "2026-10-26"
    return plan


def build_plugin() -> None:
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    base = metadata_plan()
    write_json(PLUGIN_DIR / "valid-0201.json", base)

    structured = json.loads(json.dumps(base))
    structured["activityFlow"]["taskImplementation"] = [
        {
            "mainContent": "完成第 3、4 套练习",
            "teacherActivity": "巡回指导并记录典型错误",
            "studentActivity": "完成练习并保存结果文件",
            "minutes": 35,
            "evidence": "提交第3、4套结果文件",
        }
    ]
    write_json(PLUGIN_DIR / "structured-task-missing-mustdo.json", structured)

    if C_PLAN.is_file():
        write_json(PLUGIN_DIR / "minutes-95.json", load_json(C_PLAN))

    bool_week = json.loads(json.dumps(base))
    bool_week["week"] = True
    write_json(PLUGIN_DIR / "bool-week.json", bool_week)

    missing_week = json.loads(json.dumps(base))
    del missing_week["week"]
    write_json(PLUGIN_DIR / "missing-week.json", missing_week)

    stale_plan = json.loads(json.dumps(base))
    report = adversarial_review(stale_plan, reviewer="native_subagent", no_counterexample=True)
    write_json(PLUGIN_DIR / "stale-plan.review.json", report)
    stale_plan["activityFlow"]["summary"] = "已修改课堂小结，使旧报告失效"
    write_json(PLUGIN_DIR / "stale-plan.json", stale_plan)

    expected = {
        "plugin": {
            "valid-0201.json": {"target_ok": True},
            "structured-task-missing-mustdo.json": {
                "target_ok": False,
                "issue_path": "activityFlow.taskImplementation",
                "requirement": "FR-01",
            },
            "minutes-95.json": {"target_ok": False, "requirement": "FR-01"},
            "bool-week.json": {"target_ok": False, "issue_path": "week", "requirement": "FR-01"},
            "missing-week.json": {
                "target_ok": False,
                "issue_path": "week",
                "issue_count": 1,
                "requirement": "FR-01",
            },
        },
        "stale_report": {"target_gate_ok": False, "requirement": "FR-05"},
        "platform": {
            "valid-0201.zip": {"target_status": 201},
            "tampered-title.zip": {"target_status": 422, "code": "HASH_MISMATCH"},
            "bad-schema.zip": {"target_status": 422, "code": "SCHEMA_UNSUPPORTED"},
            "media-hash-mismatch.zip": {"target_status": 422, "code": "MEDIA_MISSING"},
            "missing-media.zip": {"target_status": 422, "code": "MEDIA_MISSING"},
            "zip-slip.zip": {"target_status": 422, "code": "PAYLOAD_REJECTED"},
        },
    }
    write_json(BASE / "expected.json", expected)


def build_package(name: str, *, plan_mutator=None, manifest_mutator=None, report_mutator=None, media=True, drop_media=False) -> Path:
    target = PLATFORM_DIR / name
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    plan = metadata_plan()
    if plan_mutator:
        plan_mutator(plan)
    write_json(target / "plan.json", plan)

    report = adversarial_review(plan, reviewer="native_subagent", no_counterexample=True)
    if report_mutator:
        report_mutator(report)
    write_json(target / "plan.review.json", report)

    if media and not drop_media:
        (target / "media").mkdir()
        (target / "media" / "page-003.png").write_bytes(PNG_BYTES)

    files = []
    for path in sorted(target.rglob("*")):
        if path.is_file():
            rel = path.relative_to(target).as_posix()
            files.append({"path": rel, "sha256": sha256_file(path), "size": path.stat().st_size})
    manifest = {
        "contractVersion": "1",
        "planHash": plan_hash(plan),
        "reportHash": sha256_file(target / "plan.review.json"),
        "schemaVersion": report["schemaVersion"],
        "rubricVersion": report["rubricVersion"],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    if manifest_mutator:
        manifest_mutator(manifest)
    write_json(target / "manifest.json", manifest)
    return target


def zip_package(source: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())


def build_platform() -> None:
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    valid = build_package("valid-package")

    tampered = PLATFORM_DIR / "tampered-title-package"
    if tampered.exists():
        shutil.rmtree(tampered)
    shutil.copytree(valid, tampered)
    tampered_plan = load_json(tampered / "plan.json")
    tampered_plan["contentTitle"] = "篡改课题"
    write_json(tampered / "plan.json", tampered_plan)

    def bad_schema_manifest(manifest: dict) -> None:
        manifest["schemaVersion"] = 99

    def bad_schema_report(report: dict) -> None:
        report["schemaVersion"] = 99

    bad_schema = build_package(
        "bad-schema-package",
        manifest_mutator=bad_schema_manifest,
        report_mutator=bad_schema_report,
    )

    def media_hash(manifest: dict) -> None:
        for item in manifest["files"]:
            if item["path"].endswith("page-003.png"):
                item["sha256"] = "0" * 64

    media_bad = build_package("media-hash-mismatch-package", manifest_mutator=media_hash)

    def missing_media_entry(manifest: dict) -> None:
        manifest["files"].append(
            {
                "path": "media/page-003.png",
                "sha256": sha256_bytes(PNG_BYTES),
                "size": len(PNG_BYTES),
            }
        )

    missing_media = build_package(
        "missing-media-package", drop_media=True, manifest_mutator=missing_media_entry
    )

    zip_package(valid, PACKAGE_DIR / "valid-0201.zip")
    zip_package(tampered, PACKAGE_DIR / "tampered-title.zip")
    zip_package(bad_schema, PACKAGE_DIR / "bad-schema.zip")
    zip_package(media_bad, PACKAGE_DIR / "media-hash-mismatch.zip")
    zip_package(missing_media, PACKAGE_DIR / "missing-media.zip")

    slip_source = PLATFORM_DIR / "zip-slip-source"
    if slip_source.exists():
        shutil.rmtree(slip_source)
    slip_source.mkdir()
    write_json(slip_source / "plan.json", metadata_plan())
    with zipfile.ZipFile(PACKAGE_DIR / "zip-slip.zip", "w") as archive:
        archive.write(slip_source / "plan.json", "plan.json")
        archive.writestr("../evil.txt", "should-not-be-written")
    shutil.rmtree(slip_source)


def main() -> int:
    build_plugin()
    build_platform()
    print(f"fixtures -> {BASE}")
    print(f"plugin files: {len(list(PLUGIN_DIR.glob('*.json')))}")
    print(f"packages: {len(list(PACKAGE_DIR.glob('*.zip')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
