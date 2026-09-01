# -*- coding: utf-8 -*-
"""将校标教案 JSON 导出为带 Markdown 排版的 DOCX。"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "formatting-lesson-docx" / "scripts"))
from lib import (
    ACTIVITY_FLOW_LABELS,
    default_review_path,
    dump,
    export_gate,
    load_json,
    load_review_report,
)
from markdown_ooxml import DocxPackage, NS_W

LABEL_SHADE = "D6E3F8"
FLOW_KEYS = list(ACTIVITY_FLOW_LABELS.keys())


def _borders() -> str:
    return (
        "<w:tcBorders>"
        '<w:top w:val="single" w:sz="4" w:color="000000"/>'
        '<w:left w:val="single" w:sz="4" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="000000"/>'
        '<w:right w:val="single" w:sz="4" w:color="000000"/>'
        "</w:tcBorders>"
    )


def _cell_xml(paras: str, *, span: int = 1, shade: str | None = None, width: int | None = None) -> str:
    grid = f'<w:gridSpan w:val="{span}"/>' if span > 1 else ""
    fill = f'<w:shd w:val="clear" w:fill="{shade}"/>' if shade else ""
    cell_width = f'<w:tcW w:w="{width}" w:type="dxa"/>' if width else ""
    body = paras or "<w:p></w:p>"
    return f"<w:tc><w:tcPr>{cell_width}{grid}{_borders()}{fill}</w:tcPr>{body}</w:tc>"


def _row(cells: list[str]) -> str:
    return "<w:tr>" + "".join(cells) + "</w:tr>"


def _assets_for(plan: dict, field: str) -> list[dict]:
    items = plan.get("mediaAssets") or []
    if not isinstance(items, list):
        return []
    matched = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("attachTo") or "") == field:
            matched.append(item)
    return matched


def _field_paras(pkg: DocxPackage, plan: dict, field: str, text: str) -> str:
    xml = pkg.render_markdown(text)
    for asset in _assets_for(plan, field):
        xml += pkg.render_image_asset(asset)
    return xml


def build_document_xml(plan: dict, pkg: DocxPackage) -> str:
    flow = plan.get("activityFlow") or {}
    content = "\n".join(x for x in [plan.get("contentTitle") or "", plan.get("contentDetail") or ""] if x)
    header = (
        f"{plan.get('academicYear', '')}学年  第 {plan.get('semester', '')} 学期  "
        f"课程 {plan.get('course', '')}  编号 {plan.get('planNumber') or '____'}  "
        f"教研组 {plan.get('teachingGroup', '')}  任课教师 {plan.get('teacher') or '____'}  "
        f"教学对象 {plan.get('teachingObject') or '____'}"
    )
    date_cell = plan.get("teachDate") or f"第{plan.get('week')}周第{plan.get('session')}次"
    label_w, value_w = 1600, 7400
    rows = [
        _row(
            [
                _cell_xml(pkg.label_paragraph("授课日期"), shade=LABEL_SHADE, width=label_w),
                _cell_xml(pkg.render_markdown(str(date_cell)), width=2100),
                _cell_xml(pkg.label_paragraph("计划学时"), shade=LABEL_SHADE, width=1600),
                _cell_xml(pkg.render_markdown(str(plan.get("plannedHours", ""))), width=3700),
            ]
        ),
        _row(
            [
                _cell_xml(pkg.label_paragraph("教学内容"), shade=LABEL_SHADE, width=label_w),
                _cell_xml(_field_paras(pkg, plan, "contentTitle", content), span=3, width=value_w),
            ]
        ),
        _row(
            [
                _cell_xml(pkg.label_paragraph("教学目的"), shade=LABEL_SHADE, width=label_w),
                _cell_xml(
                    _field_paras(pkg, plan, "teachingPurpose", str(plan.get("teachingPurpose") or "")),
                    span=3,
                    width=value_w,
                ),
            ]
        ),
        _row(
            [
                _cell_xml(pkg.label_paragraph("知识目标"), shade=LABEL_SHADE, width=label_w),
                _cell_xml(
                    _field_paras(pkg, plan, "knowledgeGoals", str(plan.get("knowledgeGoals") or "")),
                    span=3,
                    width=value_w,
                ),
            ]
        ),
        _row(
            [
                _cell_xml(pkg.label_paragraph("能力目标"), shade=LABEL_SHADE, width=label_w),
                _cell_xml(
                    _field_paras(pkg, plan, "abilityGoals", str(plan.get("abilityGoals") or "")),
                    span=3,
                    width=value_w,
                ),
            ]
        ),
        _row(
            [
                _cell_xml(pkg.label_paragraph("素质目标"), shade=LABEL_SHADE, width=label_w),
                _cell_xml(
                    _field_paras(pkg, plan, "qualityGoals", str(plan.get("qualityGoals") or "")),
                    span=3,
                    width=value_w,
                ),
            ]
        ),
        _row(
            [
                _cell_xml(pkg.label_paragraph("重点与难点"), shade=LABEL_SHADE, width=label_w),
                _cell_xml(
                    _field_paras(pkg, plan, "keyPoints", str(plan.get("keyPoints") or "")),
                    span=3,
                    width=value_w,
                ),
            ]
        ),
        _row(
            [
                _cell_xml(pkg.label_paragraph("教学方法"), shade=LABEL_SHADE, width=label_w),
                _cell_xml(
                    _field_paras(pkg, plan, "teachingMethods", str(plan.get("teachingMethods") or "")),
                    span=3,
                    width=value_w,
                ),
            ]
        ),
        _row(
            [
                _cell_xml(pkg.label_paragraph("教学资源"), shade=LABEL_SHADE, width=label_w),
                _cell_xml(
                    _field_paras(pkg, plan, "teachingResources", str(plan.get("teachingResources") or "")),
                    span=3,
                    width=value_w,
                ),
            ]
        ),
    ]
    for key in FLOW_KEYS:
        text = str(flow.get(key) or "")
        paras = pkg.render_markdown(text)
        for asset in _assets_for(plan, f"activityFlow.{key}") + _assets_for(plan, key):
            paras += pkg.render_image_asset(asset)
        rows.append(
            _row(
                [
                    _cell_xml(pkg.label_paragraph(ACTIVITY_FLOW_LABELS[key]), shade=LABEL_SHADE, width=label_w),
                    _cell_xml(paras, span=3, width=value_w),
                ]
            )
        )

    table = (
        '<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/></w:tblPr>'
        '<w:tblGrid><w:gridCol w:w="1600"/><w:gridCol w:w="2100"/><w:gridCol w:w="1600"/><w:gridCol w:w="3700"/></w:tblGrid>'
        + "".join(rows)
        + "</w:tbl>"
    )
    title = pkg.label_paragraph(f"{plan.get('school', '')}教案", center=True)
    header_p = pkg.render_markdown(header)
    body = title + header_p + table
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{NS_W}">'
        "<w:body>"
        f"{body}"
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080"/>'
        "</w:sectPr></w:body></w:document>"
    )


def export_docx(plan: dict, output: Path, *, base_dir: Path | None = None) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    pkg = DocxPackage(base_dir=base_dir)
    document_xml = build_document_xml(plan, pkg)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in pkg.zip_parts(document_xml).items():
            zf.writestr(name, data)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="导出教案 DOCX")
    parser.add_argument("path", help="教案 JSON")
    parser.add_argument("-o", "--out", help="输出 docx 路径")
    parser.add_argument("--review", help="对抗审查报告路径；默认读取教案同目录 .review.json")
    args = parser.parse_args()
    plan_path = Path(args.path)
    plan = load_json(plan_path)
    review_path = Path(args.review) if args.review else default_review_path(plan_path)
    if not review_path.is_file():
        report = None
    else:
        try:
            report = load_review_report(review_path)
        except (OSError, ValueError, json.JSONDecodeError):
            print(dump({"ok": False, "reasons": [f"审查报告无法解析：{review_path.as_posix()}"]}), file=sys.stderr)
            return 1
    gate = export_gate(plan, report)
    if not gate["ok"]:
        print(dump({"ok": False, "reasons": gate["reasons"]}), file=sys.stderr)
        return 1
    week = plan.get("week")
    session = plan.get("session")
    out = Path(args.out) if args.out else plan_path.parent / f"教案_第{week}周第{session}次.docx"
    saved = export_docx(plan, out, base_dir=plan_path.parent)
    print(f'{{"ok": true, "path": "{saved.as_posix()}", "bytes": {saved.stat().st_size}}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
