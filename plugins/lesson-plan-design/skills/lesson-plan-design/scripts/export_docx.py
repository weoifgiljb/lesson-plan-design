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

LABEL_SHADE = "E7E7E7"
HEADER_SHADE = "D9D9D9"
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
    padding = (
        '<w:tcMar><w:top w:w="90" w:type="dxa"/><w:left w:w="110" w:type="dxa"/>'
        '<w:bottom w:w="90" w:type="dxa"/><w:right w:w="110" w:type="dxa"/></w:tcMar>'
    )
    body = paras or "<w:p></w:p>"
    return f"<w:tc><w:tcPr>{cell_width}{grid}{_borders()}{fill}{padding}<w:vAlign w:val=\"top\"/></w:tcPr>{body}</w:tc>"


def _row(cells: list[str], *, header: bool = False) -> str:
    trpr = '<w:trPr><w:cantSplit/>'
    if header:
        trpr += '<w:tblHeader/>'
    trpr += '</w:trPr>'
    return "<w:tr>" + trpr + "".join(cells) + "</w:tr>"


def _table_xml(rows: list[str], widths: list[int]) -> str:
    total = sum(widths)
    grid = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    return (
        f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/><w:tblCellMar>'
        '<w:top w:w="90" w:type="dxa"/><w:left w:w="110" w:type="dxa"/>'
        '<w:bottom w:w="90" w:type="dxa"/><w:right w:w="110" w:type="dxa"/>'
        '</w:tblCellMar></w:tblPr>'
        f'<w:tblGrid>{grid}</w:tblGrid>'
        + "".join(rows)
        + "</w:tbl>"
    )


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


def _structured_activities(value: object) -> list[dict] | None:
    """Return structured activities, while leaving legacy strings untouched."""
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list) or not value or not all(isinstance(item, dict) for item in value):
        return None
    return value


def _activity_text(item: dict, field: str) -> str:
    value = item.get(field)
    if value is None:
        return ""
    return str(value).strip()


def _activity_label(label: str, item: dict) -> str:
    minutes = item.get("minutes")
    if minutes in (None, ""):
        return label
    return f"{label}\n（{minutes}分钟）"


def _activity_markdown(item: dict) -> str:
    sections = []
    for field, label in (
        ("mainContent", "主要内容"),
        ("teacherActivity", "教师活动"),
        ("studentActivity", "学生活动"),
        ("evidence", "产出"),
    ):
        value = _activity_text(item, field)
        if value:
            sections.append(f"**{label}：** {value}")
    return "\n\n".join(sections)


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
    # A4 width minus 1.25in side margins leaves approximately 8,300 twips.
    label_w, value_w = 1300, 7000
    rows = [
        _row(
            [
                _cell_xml(pkg.label_paragraph("授课日期"), shade=LABEL_SHADE, width=1300),
                _cell_xml(pkg.render_markdown(str(date_cell)), width=2000),
                _cell_xml(pkg.label_paragraph("计划学时"), shade=LABEL_SHADE, width=1300),
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
    metadata_table = _table_xml(rows, [1300, 2000, 1300, 3700])
    flow_rows = [
        _row(
            [
                _cell_xml(pkg.label_paragraph("教学环节"), shade=HEADER_SHADE, width=1300),
                _cell_xml(pkg.label_paragraph("教学内容"), shade=HEADER_SHADE, width=7000),
            ],
            header=True,
        )
    ]
    for key in FLOW_KEYS:
        value = flow.get(key)
        activities = _structured_activities(value)
        if activities is None:
            text = str(value or "")
            paras = pkg.render_markdown(text)
            for asset in _assets_for(plan, f"activityFlow.{key}") + _assets_for(plan, key):
                paras += pkg.render_image_asset(asset)
            flow_rows.append(
                _row(
                    [
                        _cell_xml(pkg.label_paragraph(ACTIVITY_FLOW_LABELS[key]), shade=LABEL_SHADE, width=1300),
                        _cell_xml(paras, width=7000),
                    ]
                )
            )
            continue
        for item in activities:
            flow_rows.append(
                _row(
                    [
                        _cell_xml(pkg.render_markdown(_activity_label(ACTIVITY_FLOW_LABELS[key], item)), shade=LABEL_SHADE, width=1300),
                        _cell_xml(pkg.render_markdown(_activity_markdown(item)), width=7000),
                    ]
                )
            )
        assets = _assets_for(plan, f"activityFlow.{key}") + _assets_for(plan, key)
        if assets:
            asset_xml = "".join(pkg.render_image_asset(asset) for asset in assets)
            flow_rows.append(
                _row(
                    [
                        _cell_xml(pkg.label_paragraph(ACTIVITY_FLOW_LABELS[key]), shade=LABEL_SHADE, width=1300),
                        _cell_xml(asset_xml, width=7000),
                    ]
                )
            )
    flow_table = _table_xml(flow_rows, [1300, 7000])
    title = pkg.title_paragraph(f"{plan.get('school', '')}教案")
    header_p = pkg.render_markdown(header)
    body = title + header_p + metadata_table + flow_table
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{NS_W}">'
        "<w:body>"
        f"{body}"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1800" w:bottom="1440" w:left="1800"/>'
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
