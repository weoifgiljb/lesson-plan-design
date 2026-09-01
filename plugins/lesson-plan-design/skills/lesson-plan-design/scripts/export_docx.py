# -*- coding: utf-8 -*-
"""将校标教案 JSON 导出为最小 DOCX（仅标准库 zip/xml）。"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (
    ACTIVITY_FLOW_LABELS,
    default_review_path,
    dump,
    export_gate,
    load_json,
    load_review_report,
)

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>
"""


def _p(text: str, *, bold: bool = False, center: bool = False) -> str:
    align = '<w:jc w:val="center"/>' if center else ""
    rpr = "<w:rPr><w:b/><w:rFonts w:ascii=\"宋体\" w:eastAsia=\"宋体\"/></w:rPr>" if bold else "<w:rPr><w:rFonts w:ascii=\"宋体\" w:eastAsia=\"宋体\"/></w:rPr>"
    lines = text.split("\n") or [""]
    parts = []
    for line in lines:
        parts.append(
            f'<w:p><w:pPr>{align}</w:pPr><w:r>{rpr}<w:t xml:space="preserve">{escape(line)}</w:t></w:r></w:p>'
        )
    return "".join(parts)


def _cell(text: str, *, span: int = 1, bold: bool = False) -> str:
    grid = f'<w:gridSpan w:val="{span}"/>' if span > 1 else ""
    paras = _p(text, bold=bold)
    return (
        f'<w:tc><w:tcPr>{grid}<w:tcBorders>'
        f'<w:top w:val="single" w:sz="4" w:color="000000"/>'
        f'<w:left w:val="single" w:sz="4" w:color="000000"/>'
        f'<w:bottom w:val="single" w:sz="4" w:color="000000"/>'
        f'<w:right w:val="single" w:sz="4" w:color="000000"/>'
        f'</w:tcBorders></w:tcPr>{paras}</w:tc>'
    )


def _row(cells: list[str]) -> str:
    return "<w:tr>" + "".join(cells) + "</w:tr>"


def build_document_xml(plan: dict) -> str:
    flow = plan.get("activityFlow") or {}
    flow_text = "\n\n".join(
        [
            f"{ACTIVITY_FLOW_LABELS['introduction']}{flow.get('introduction', '')}",
            f"{ACTIVITY_FLOW_LABELS['learningGoals']}{flow.get('learningGoals', '')}",
            f"{ACTIVITY_FLOW_LABELS['knowledgeLearning']}\n{flow.get('knowledgeLearning', '')}",
            f"{ACTIVITY_FLOW_LABELS['taskImplementation']}\n{flow.get('taskImplementation', '')}",
            f"{ACTIVITY_FLOW_LABELS['assessment']}\n{flow.get('assessment', '')}",
            f"{ACTIVITY_FLOW_LABELS['summary']}{flow.get('summary', '')}",
            f"{ACTIVITY_FLOW_LABELS['homework']}{flow.get('homework', '')}",
            f"{ACTIVITY_FLOW_LABELS['reflection']}{flow.get('reflection', '')}",
        ]
    )
    content = "\n".join(x for x in [plan.get("contentTitle") or "", plan.get("contentDetail") or ""] if x)
    header = (
        f"{plan.get('academicYear','')}学年  第 {plan.get('semester','')} 学期  "
        f"课程 {plan.get('course','')}  编号 {plan.get('planNumber') or '____'}  "
        f"教研组 {plan.get('teachingGroup','')}  任课教师 {plan.get('teacher') or '____'}  "
        f"教学对象 {plan.get('teachingObject') or '____'}"
    )
    date_cell = plan.get("teachDate") or f"第{plan.get('week')}周第{plan.get('session')}次"
    rows = [
        _row([_cell("授课日期", bold=True), _cell(str(date_cell)), _cell("计划学时", bold=True), _cell(str(plan.get("plannedHours", "")))]),
        _row([_cell("教学内容", bold=True), _cell(content, span=3)]),
        _row([_cell("教学目的", bold=True), _cell(str(plan.get("teachingPurpose") or ""), span=3)]),
        _row([_cell("知识目标", bold=True), _cell(str(plan.get("knowledgeGoals") or ""), span=3)]),
        _row([_cell("能力目标", bold=True), _cell(str(plan.get("abilityGoals") or ""), span=3)]),
        _row([_cell("素质目标", bold=True), _cell(str(plan.get("qualityGoals") or ""), span=3)]),
        _row([_cell("重点与难点", bold=True), _cell(str(plan.get("keyPoints") or ""), span=3)]),
        _row([_cell("教学方法", bold=True), _cell(str(plan.get("teachingMethods") or ""), span=3)]),
        _row([_cell("教学资源", bold=True), _cell(str(plan.get("teachingResources") or ""), span=3)]),
        _row([_cell("教学活动流程", bold=True), _cell(flow_text, span=3)]),
    ]
    table = (
        '<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/></w:tblPr>'
        + "".join(rows)
        + "</w:tbl>"
    )
    body = _p(f"{plan.get('school','')}教案", bold=True, center=True) + _p(header) + table
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/><w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\"/></w:sectPr></w:body></w:document>"
    )


def export_docx(plan: dict, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
        zf.writestr("word/document.xml", build_document_xml(plan))
    return output


def main() -> int:
    p = argparse.ArgumentParser(description="导出教案 DOCX")
    p.add_argument("path", help="教案 JSON")
    p.add_argument("-o", "--out", help="输出 docx 路径")
    p.add_argument("--review", help="对抗审查报告路径；默认读取教案同目录 .review.json")
    args = p.parse_args()
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
    saved = export_docx(plan, out)
    print(f'{{"ok": true, "path": "{saved.as_posix()}", "bytes": {saved.stat().st_size}}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
