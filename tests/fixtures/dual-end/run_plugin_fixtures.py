# -*- coding: utf-8 -*-
"""执行双端测试样例中的插件端用例，并核验平台端契约包与源目录一致性。

用法：py -3 tests/fixtures/dual-end/run_plugin_fixtures.py
退出码 1 表示存在未达标的验收项（对应需求 FR-01、FR-05 等）或夹具 manifest 漂移。
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
SKILL_SCRIPTS = ROOT / "plugins" / "lesson-plan-design" / "skills" / "lesson-plan-design" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from lib import export_gate, load_json, plan_hash, validate_plan  # noqa: E402

EXPECTED = json.loads((BASE / "expected.json").read_text(encoding="utf-8"))
PLUGIN = BASE / "plugin"
PLATFORM = BASE / "platform"
PACKAGES = PLATFORM / "packages"

# 这些包的 manifest 故意与文件不一致，用来模拟篡改/缺媒体；校验时只豁免指定路径。
INTENTIONAL_MISMATCH = {
    "tampered-title-package": {"plan.json"},
    "media-hash-mismatch-package": {"media/page-003.png"},
    "missing-media-package": {"media/page-003.png"},
}
ZIP_TO_DIR = {
    "valid-0201.zip": "valid-package",
    "tampered-title.zip": "tampered-title-package",
    "bad-schema.zip": "bad-schema-package",
    "media-hash-mismatch.zip": "media-hash-mismatch-package",
    "missing-media.zip": "missing-media-package",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_plugin() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    for name, spec in EXPECTED["plugin"].items():
        plan = load_json(PLUGIN / name)
        result = validate_plan(plan)
        target = spec["target_ok"]
        passed = result["ok"] == target
        detail = f"当前 ok={result['ok']}，目标 ok={target}"
        issue_path = spec.get("issue_path")
        if issue_path:
            hits = [item for item in result["issues"] if item["path"] == issue_path]
            expected_count = spec.get("issue_count")
            if expected_count is not None:
                path_ok = len(hits) == expected_count
                detail += f"；{issue_path} 问题 {len(hits)} 条（目标 {expected_count}）"
                passed = passed and path_ok
            elif not target:
                passed = passed and bool(hits)
                detail += f"；{issue_path} 问题 {len(hits)} 条"
        results.append((f"插件 {name}", passed, detail))
    return results


def check_stale_report() -> list[tuple[str, bool, str]]:
    plan = load_json(PLUGIN / "stale-plan.json")
    report = load_json(PLUGIN / "stale-plan.review.json")
    gate = export_gate(plan, report)
    target = EXPECTED["stale_report"]["target_gate_ok"]
    reason_ok = any("不匹配" in reason for reason in gate["reasons"])
    passed = gate["ok"] == target and reason_ok
    detail = f"当前 gate.ok={gate['ok']}，原因 {'；'.join(gate['reasons'])[:60]}"
    return [("插件 stale-plan 旧报告失效", passed, detail)]


def check_package_sources() -> list[tuple[str, bool, str]]:
    """核验 platform/*-package 的 manifest 与磁盘文件一致，防止夹具漂移。"""
    results: list[tuple[str, bool, str]] = []
    for directory in sorted(PLATFORM.glob("*-package")):
        manifest_path = directory / "manifest.json"
        plan_path = directory / "plan.json"
        report_path = directory / "plan.review.json"
        problems: list[str] = []
        if not (manifest_path.is_file() and plan_path.is_file() and report_path.is_file()):
            results.append((f"夹具 {directory.name}", False, "缺少 manifest/plan/report"))
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        report_bytes = report_path.read_bytes()
        skip = INTENTIONAL_MISMATCH.get(directory.name, set())
        if "plan.json" not in skip and manifest.get("planHash") != plan_hash(plan):
            problems.append("planHash 不一致")
        if manifest.get("reportHash") != hashlib.sha256(report_bytes).hexdigest():
            problems.append("reportHash 不一致")
        declared = {item["path"] for item in manifest.get("files", [])}
        for item in manifest.get("files", []):
            path = directory / item["path"]
            if item["path"] in skip:
                continue
            if not path.is_file():
                problems.append(f"缺文件 {item['path']}")
                continue
            data = path.read_bytes()
            if len(data) != item["size"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                problems.append(f"{item['path']} 大小/哈希不一致")
        actual = {
            path.relative_to(directory).as_posix()
            for path in directory.rglob("*")
            if path.is_file() and path.name != "manifest.json"
        }
        extra = sorted(actual - declared)
        if extra:
            problems.append(f"未声明文件 {extra}")
        results.append(
            (
                f"夹具 {directory.name} manifest 一致",
                not problems,
                "；".join(problems) if problems else "plan/report/媒体与 manifest 一致",
            )
        )
    return results


def check_package_zips() -> list[tuple[str, bool, str]]:
    """核验 packages/*.zip 与同名 *-package 目录逐文件一致。"""
    results: list[tuple[str, bool, str]] = []
    for zip_name, dir_name in ZIP_TO_DIR.items():
        zip_path = PACKAGES / zip_name
        directory = PLATFORM / dir_name
        if not zip_path.is_file() or not directory.is_dir():
            results.append((f"夹具 {zip_name} ↔ {dir_name}", False, "zip 或目录缺失"))
            continue
        expected = {
            path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob("*")
            if path.is_file()
        }
        with zipfile.ZipFile(zip_path) as archive:
            actual_names = set(archive.namelist())
            missing = sorted(set(expected) - actual_names)
            extra = sorted(actual_names - set(expected))
            changed = sorted(
                name
                for name in set(expected) & actual_names
                if archive.read(name) != expected[name]
            )
        problems = []
        if missing:
            problems.append(f"缺条目 {missing}")
        if extra:
            problems.append(f"多条目 {extra}")
        if changed:
            problems.append(f"内容不一致 {changed}")
        results.append(
            (
                f"夹具 {zip_name} ↔ {dir_name}",
                not problems,
                "；".join(problems) if problems else "zip 与目录逐文件一致",
            )
        )
    return results


def check_zip(name: str) -> list[tuple[str, bool, str]]:
    path = PACKAGES / name
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if name == "zip-slip.zip":
            bad = any(item.startswith("../") or "/../" in item for item in names)
            return [("平台 zip-slip 可检出", bad, f"包含非法条目 {[n for n in names if '..' in n]}")]
        manifest = json.loads(archive.read("manifest.json"))
        plan = json.loads(archive.read("plan.json"))
        report_bytes = archive.read("plan.review.json")
        file_hashes = {
            item["path"]: hashlib.sha256(archive.read(item["path"])).hexdigest()
            for item in manifest["files"]
            if item["path"] in names
        }
        media_bytes = archive.read("media/page-003.png") if "media/page-003.png" in names else b""
    results: list[tuple[str, bool, str]] = []
    if name == "valid-0201.zip":
        hash_ok = manifest["planHash"] == plan_hash(plan)
        report_ok = manifest["reportHash"] == hashlib.sha256(report_bytes).hexdigest()
        files_ok = all(item["sha256"] == file_hashes.get(item["path"]) for item in manifest["files"])
        results.append(("平台 valid-0201 包完整性", hash_ok and report_ok and files_ok, "哈希与文件一致"))
    elif name == "tampered-title.zip":
        mismatch = manifest["planHash"] != plan_hash(plan)
        results.append(("平台 tampered-title 可检出篡改", mismatch, "教案哈希与声明不一致"))
    elif name == "bad-schema.zip":
        results.append(("平台 bad-schema 版本异常", manifest["schemaVersion"] == 99, "manifest 版本 99"))
    elif name == "media-hash-mismatch.zip":
        entries = [item for item in manifest["files"] if item["path"].endswith("page-003.png")]
        mismatch = bool(entries) and entries[0]["sha256"] != hashlib.sha256(media_bytes).hexdigest()
        results.append(("平台 media-hash-mismatch 可检出", mismatch, "媒体哈希与文件不一致"))
    elif name == "missing-media.zip":
        referenced = any(item["path"] == "media/page-003.png" for item in manifest["files"])
        missing = "media/page-003.png" not in names
        results.append(("平台 missing-media 可检出", referenced and missing, "manifest 引用缺失媒体"))
    return results


def check_platform() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    for name in EXPECTED["platform"]:
        results.extend(check_zip(name))
    return results


def main() -> int:
    rows = (
        check_package_sources()
        + check_package_zips()
        + check_plugin()
        + check_stale_report()
        + check_platform()
    )
    print(f"{'检查项':<44} 结果  说明")
    print("-" * 100)
    failed = 0
    for name, passed, detail in rows:
        if not passed:
            failed += 1
        print(f"{name:<44} {'PASS' if passed else 'FAIL'}  {detail}")
    print("-" * 100)
    print(f"共 {len(rows)} 项，通过 {len(rows) - failed} 项，未达标 {failed} 项")
    if failed:
        print("未达标项对应插件端 FR-01 / FR-05 等待修复需求，或夹具 manifest 与磁盘漂移；修复后本脚本应全部通过。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
