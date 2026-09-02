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
    default_review_path,
    dump,
    export_gate,
    load_json,
    load_review_report,
)
from markdown_ooxml import DocxPackage, NS_W

LABEL_SHADE = "E7E7E7"
HEADER_SHADE = "D9D9D9"


def _borders() -> str:
    return (
        "<w:tcBorders>"
        '<w:top w:val="single" w:sz="4" w:color="000000"/>'
        '<w:left w:val="single" w:sz="4" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="000000"/>'
        '<w:right w:val="single" w:sz="4" w:color="000000"/>'
        "</w:tcBorders>"
    )


def _cell_xml(
    paras: str,
    *,
    span: int = 1,
    shade: str | None = None,
    width: int | None = None,
    vmerge: str | None = None,
    valign: str = "top",
) -> str:
    grid = f'<w:gridSpan w:val="{span}"/>' if span > 1 else ""
    fill = f'<w:shd w:val="clear" w:fill="{shade}"/>' if shade else ""
    cell_width = f'<w:tcW w:w="{width}" w:type="dxa"/>' if width else ""
    padding = (
        '<w:tcMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tcMar>'
    )
    body = paras or "<w:p></w:p>"
    merge = f'<w:vMerge w:val="{vmerge}"/>' if vmerge else ""
    return f"<w:tc><w:tcPr>{cell_width}{grid}{merge}{_borders()}{fill}{padding}<w:vAlign w:val=\"{valign}\"/></w:tcPr>{body}</w:tc>"


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
        '<w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/>'
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


def build_document_xml(plan: dict, pkg: DocxPackage) -> str:
    """Build the reference-style single table used by the supplied teaching design."""
    flow = plan.get("activityFlow") or {}
    content = "\n".join(x for x in [plan.get("contentTitle") or "", plan.get("contentDetail") or ""] if x)
    widths = [827, 274, 1275, 1985, 2551, 664, 1001, 711]
    full_w = sum(widths)
    rows: list[str] = []

    rows.append(_row([
        _cell_xml(pkg.label_paragraph("教学内容", center=True), shade=LABEL_SHADE, span=2, width=1101, valign="center"),
        _cell_xml(_field_paras(pkg, plan, "contentTitle", content), shade=LABEL_SHADE, span=4, width=6475),
        _cell_xml(pkg.label_paragraph("课时", center=True), shade=LABEL_SHADE, width=1001, valign="center"),
        _cell_xml(pkg.render_markdown(str(plan.get("plannedHours", ""))), shade=LABEL_SHADE, width=711),
    ]))
    goals = [("知识目标", "knowledgeGoals"), ("能力目标", "abilityGoals"), ("素质目标", "qualityGoals")]
    for index, (label, field) in enumerate(goals):
        rows.append(_row([
            _cell_xml(pkg.label_paragraph("教学目标" if index == 0 else "", center=True), shade=LABEL_SHADE, span=2, width=1101, vmerge="restart" if index == 0 else "continue", valign="center"),
            _cell_xml(pkg.label_paragraph(label, center=True), width=1275, valign="center"),
            _cell_xml(_field_paras(pkg, plan, field, str(plan.get(field) or "")), span=5, width=6912),
        ]))
    for label, field in (("教学重点", "keyPoints"), ("教学难点", "keyPoints"), ("教学方法", "teachingMethods"), ("教学准备", "teachingResources")):
        rows.append(_row([
            _cell_xml(pkg.label_paragraph(label, center=True), shade=LABEL_SHADE, span=2, width=1101, valign="center"),
            _cell_xml(_field_paras(pkg, plan, field, str(plan.get(field) or "")), span=6, width=8187),
        ]))

    rows.append(_row([_cell_xml(pkg.label_paragraph("教学过程", center=True), shade=HEADER_SHADE, span=8, width=full_w, valign="center")], header=True))
    rows.append(_row([
        _cell_xml(pkg.label_paragraph("教学环节", center=True), shade=HEADER_SHADE, width=827, vmerge="restart", valign="center"),
        _cell_xml(pkg.label_paragraph("主要内容", center=True), shade=HEADER_SHADE, span=3, width=3534, vmerge="restart", valign="center"),
        _cell_xml(pkg.label_paragraph("教学活动", center=True), shade=HEADER_SHADE, span=4, width=4927, valign="center"),
    ], header=True))
    rows.append(_row([
        _cell_xml("", shade=HEADER_SHADE, width=827, vmerge="continue", valign="center"),
        _cell_xml("", shade=HEADER_SHADE, span=3, width=3534, vmerge="continue", valign="center"),
        _cell_xml(pkg.label_paragraph("教师活动", center=True), shade=HEADER_SHADE, width=2551, valign="center"),
        _cell_xml(pkg.label_paragraph("学生活动", center=True), shade=HEADER_SHADE, span=3, width=2376, valign="center"),
    ], header=True))

    groups = [
        ("课前组织", ("introduction",)),
        ("导入新课", ("learningGoals",)),
        ("知识学习", ("knowledgeLearning",)),
        ("任务实施与考核", ("taskImplementation", "assessment")),
        ("课堂小结", ("summary",)),
        ("课后作业与反思", ("homework", "reflection")),
    ]
    for label, keys in groups:
        main_parts: list[str] = []
        teacher_parts: list[str] = []
        student_parts: list[str] = []
        assets = []
        for key in keys:
            value = flow.get(key)
            activities = _structured_activities(value)
            if activities is None:
                if value:
                    main_parts.append(str(value))
            else:
                for item in activities:
                    if _activity_text(item, "mainContent"):
                        main_parts.append(_activity_text(item, "mainContent"))
                    if _activity_text(item, "teacherActivity"):
                        teacher_parts.append(_activity_text(item, "teacherActivity"))
                    student = _activity_text(item, "studentActivity")
                    evidence = _activity_text(item, "evidence")
                    if evidence:
                        student = "\n".join(x for x in (student, f"产出：{evidence}") if x)
                    if student:
                        student_parts.append(student)
            assets.extend(_assets_for(plan, f"activityFlow.{key}") + _assets_for(plan, key))
        main_xml = pkg.render_markdown("\n\n".join(main_parts))
        for asset in assets:
            main_xml += pkg.render_image_asset(asset)
        rows.append(_row([
            _cell_xml(pkg.label_paragraph(label, center=True), shade=LABEL_SHADE, width=827, valign="center"),
            _cell_xml(main_xml, span=3, width=3534),
            _cell_xml(pkg.render_markdown("\n\n".join(teacher_parts)), width=2551),
            _cell_xml(pkg.render_markdown("\n\n".join(student_parts)), span=3, width=2376),
        ]))

    table = _table_xml(rows, widths)
    title = pkg.title_paragraph(f"《{plan.get('contentTitle') or '未命名课题'}》")
    body = title + table
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{NS_W}"><w:body>{body}'
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
