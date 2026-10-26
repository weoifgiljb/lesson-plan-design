# -*- coding: utf-8 -*-
"""将校标教案 JSON 导出为带 Markdown 排版的 DOCX。"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "formatting-lesson-docx" / "scripts"))
from _cli import CliError, JsonArgumentParser, run_cli
from lib import default_review_path, dump, export_gate, load_json, load_review_report
from markdown_ooxml import DocxPackage

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
    strict_metadata: bool = False,
) -> dict:
    if strict_metadata:
        missing = _missing_metadata(plan)
        if missing:
            raise ValueError("严格模式缺少元信息：" + "、".join(missing))
    output.parent.mkdir(parents=True, exist_ok=True)
    pkg = DocxPackage(base_dir=base_dir)
    pkg.footer_xml = _footer_xml(plan)
    document_xml = build_document_xml(plan, pkg, independence=independence)
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
    return {
        "path": output,
        "warnings": warnings,
        "media": media,
        "engineVersion": ENGINE_VERSION,
    }


def export_docx(
    plan: dict,
    output: Path,
    *,
    base_dir: Path | None = None,
    independence: str | None = None,
    strict_metadata: bool = False,
) -> Path:
    return export_docx_result(
        plan,
        output,
        base_dir=base_dir,
        independence=independence,
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
    args = parser.parse_args()
    plan_path = Path(args.path)
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
    week = plan.get("week")
    session = plan.get("session")
    out = Path(args.out) if args.out else plan_path.parent / f"教案_第{week}周第{session}次.docx"
    independence = None
    if isinstance(report, dict):
        independence = report.get("independence") or report.get("reviewer")
    result = export_docx_result(
        plan,
        out,
        base_dir=plan_path.parent,
        independence=independence,
        strict_metadata=args.strict_metadata,
    )
    check = self_check(Path(result["path"]), plan, result["media"])
    if not check["ok"]:
        raise CliError("EXPORT_SELF_CHECK_FAILED", "导出后自检未通过", "检查页脚与媒体文件")
    print(dump({
        "ok": True,
        "path": str(result["path"]),
        "bytes": Path(result["path"]).stat().st_size,
        "engineVersion": result["engineVersion"],
        "selfCheck": check,
        "warnings": result["warnings"],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(run_cli(main))