# -*- coding: utf-8 -*-
"""执行双端测试样例中的插件端用例，并静态核验平台端契约包。

用法：py -3 tests/fixtures/dual-end/run_plugin_fixtures.py
退出码 1 表示存在未达标的验收项（对应需求 FR-01、FR-05 等，修复后应转绿）。
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
    rows = check_plugin() + check_stale_report() + check_platform()
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
        print("未达标项对应插件端 FR-01 / FR-05 等待修复需求；修复后本脚本应全部通过。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
