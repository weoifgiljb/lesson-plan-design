# -*- coding: utf-8 -*-
"""将校标教案 JSON 导出为带 Markdown 排版的 DOCX。"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "formatting-lesson-docx" / "scripts"))
from _cli import CliError, JsonArgumentParser, run_cli
from export_history import BACKUP_SUFFIX, default_output, history_path, load_history, record_history
from lib import default_review_path, dump, export_gate, load_json, load_review_report
from markdown_ooxml import DocxPackage

from docx_export.build import build_document_xml
from docx_export.content import _split_key_points
from docx_export.footer import ENGINE_VERSION, _footer_xml
from docx_export.metadata import _missing_metadata
from docx_export.selfcheck import self_check


from docx_export.build import build_document_xml
from docx_export.content import _split_key_points
from docx_export.footer import ENGINE_VERSION, _footer_xml
from docx_export.metadata import _missing_metadata
from docx_export.selfcheck import self_check


def export_docx_result(
    plan: dict,
    output: Path,
    *,
    base_dir: Path | None = None,
    independence: str | None = None,
    overrides: list[dict] | None = None,
    strict_metadata: bool = False,
) -> dict:
    missing_metadata = _missing_metadata(plan)
    if strict_metadata and missing_metadata:
        raise ValueError("严格模式缺少元信息：" + "、".join(missing_metadata))
    output.parent.mkdir(parents=True, exist_ok=True)
    exported = datetime.now().astimezone()
    exported_label = exported.strftime("%Y-%m-%d %H:%M")
    pkg = DocxPackage(base_dir=base_dir)
    pkg.core_properties = {
        "title": f"{plan.get('contentTitle') or '未命名课题'} 教案",
        "creator": str(plan.get("teacher") or "lesson-plan-design"),
        "lastModifiedBy": f"lesson-plan-design {ENGINE_VERSION}",
        "created": exported.astimezone(timezone.utc).isoformat(timespec="seconds"),
    }
    pkg.footer_xml = _footer_xml(plan, exported_label)
    document_xml = build_document_xml(plan, pkg, independence=independence, overrides=overrides)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in pkg.zip_parts(document_xml).items():
            zf.writestr(name, data)
    media = []
    for _rid, dest, path in pkg._images:
        data = path.read_bytes()
        media.append({
            "dest": dest,
            "source": str(path),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    warnings = [
        f"图片缺失：{src}" for src in dict.fromkeys(pkg.missing_images)
    ]
    if missing_metadata:
        warnings.append("元信息缺失：" + "、".join(missing_metadata))
    return {
        "path": output,
        "warnings": warnings,
        "media": media,
        "engineVersion": ENGINE_VERSION,
        "stats": {
            "media": len(media),
            "warnings": len(warnings),
            "bytes": output.stat().st_size,
            "exportedAt": exported.isoformat(timespec="seconds"),
        },
    }


def export_docx(
    plan: dict,
    output: Path,
    *,
    base_dir: Path | None = None,
    independence: str | None = None,
    overrides: list[dict] | None = None,
    strict_metadata: bool = False,
) -> Path:
    return export_docx_result(
        plan,
        output,
        base_dir=base_dir,
        independence=independence,
        overrides=overrides,
        strict_metadata=strict_metadata,
    )["path"]



def main() -> int:
    parser = JsonArgumentParser(description="导出教案 DOCX")
    parser.add_argument("path", help="教案 JSON")
    parser.add_argument("-o", "--out", help="输出 docx 路径")
    parser.add_argument("--review", help="对抗审查报告路径；默认读取教案同目录 .review.json")
    parser.add_argument(
        "--strict-independence",
        action="store_true",
        help="严格模式拒绝角色模拟审校，要求独立子代理或人工审校",
    )
    parser.add_argument(
        "--strict-metadata",
        action="store_true",
        help="导出前要求任课教师、教学对象、授课日期非空",
    )
    parser.add_argument("--force", action="store_true", help="目标已存在时覆盖，覆盖前保留 .bak")
    parser.add_argument("--history", action="store_true", help="列出本教案的导出历史")
    parser.add_argument("--open-version", type=int, default=None, help="输出指定历史版本的路径")
    args = parser.parse_args()
    plan_path = Path(args.path)
    if args.history:
        print(dump({"ok": True, "history": load_history(plan_path)}))
        return 0
    if args.open_version is not None:
        entry = next((item for item in load_history(plan_path) if item.get("version") == args.open_version), None)
        if entry is None:
            raise CliError("VERSION_NOT_FOUND", f"没有第 {args.open_version} 版导出记录", "先运行 --history 查看版本")
        stored = Path(str(entry["path"]))
        path = stored if stored.is_absolute() else plan_path.parent / stored
        print(dump({"ok": True, "path": str(path), "entry": entry}))
        return 0
    plan = load_json(plan_path)
    review_path = Path(args.review) if args.review else default_review_path(plan_path)
    if not review_path.is_file():
        report = None
    else:
        try:
            report = load_review_report(review_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise CliError(
                "INVALID_JSON",
                f"审查报告无法解析：{review_path.as_posix()}",
                "检查报告 JSON 语法与编码",
            ) from exc
    gate = export_gate(plan, report, strict_independence=args.strict_independence)
    if not gate["ok"]:
        raise CliError("GATE_REJECTED", "导出被门禁拒绝", "；".join(gate["reasons"]))
    history = load_history(plan_path)
    version = len(history) + 1
    out = Path(args.out) if args.out else default_output(plan, plan_path, version)
    if out.exists():
        if not args.force:
            raise CliError(
                "OUTPUT_EXISTS",
                f"目标文件已存在：{out.name}",
                "确认覆盖时加 --force；覆盖前会自动保留 .bak",
            )
        shutil.copy2(out, out.with_name(out.name + BACKUP_SUFFIX))
    independence = None
    overrides = None
    if isinstance(report, dict):
        independence = report.get("independence") or report.get("reviewer")
        overrides = report.get("overrides") if isinstance(report.get("overrides"), list) else None
    working = out.with_name(out.name + ".tmp")
    try:
        result = export_docx_result(
            plan,
            working,
            base_dir=plan_path.parent,
            independence=independence,
            overrides=overrides,
            strict_metadata=args.strict_metadata,
        )
        check = self_check(working, plan, result["media"])
        if not check["ok"]:
            raise CliError("EXPORT_SELF_CHECK_FAILED", "导出后自检未通过", "检查页脚与媒体文件")
        working.replace(out)
    finally:
        if working.exists():
            working.unlink()
    history_file = record_history(plan_path, out, plan, version)
    print(dump({
        "ok": True,
        "path": str(out),
        "bytes": out.stat().st_size,
        "version": version,
        "backup": str(out.with_name(out.name + BACKUP_SUFFIX)) if out.with_name(out.name + BACKUP_SUFFIX).exists() else None,
        "history": str(history_file),
        "engineVersion": result["engineVersion"],
        "selfCheck": check,
        "warnings": result["warnings"],
        "stats": result["stats"],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(run_cli(main))