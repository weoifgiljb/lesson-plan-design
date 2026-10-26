# -*- coding: utf-8 -*-
"""将校标教案 JSON 导出为带 Markdown 排版的 DOCX。"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
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
    plan_hash,
)
from markdown_ooxml import DocxPackage, NS_W

ENGINE_VERSION = "1.0.0"
LABEL_SHADE = "E7E7E7"
HEADER_SHADE = "D9D9D9"
COL_WIDTHS = [827, 274, 1275, 1985, 2551, 664, 1001, 711]
_KEY_DIFF_RE = re.compile(r"难点[:：]")
_KEY_PREFIX_RE = re.compile(r"^重点[:：]\s*")


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


def _activity_label(label: str, item: dict) -> str:
    minutes = item.get("minutes")
    if minutes in (None, ""):
        return label
    return f"{label}\n（{minutes}分钟）"


def _split_key_points(text: str) -> tuple[str, str]:
    """Split `重点：…难点：…` into two cells; otherwise keep the whole text as 重点."""
    raw = (text or "").strip()
    if not raw:
        return "", ""
    if _KEY_DIFF_RE.search(raw):
        before, after = _KEY_DIFF_RE.split(raw, maxsplit=1)
        key = _KEY_PREFIX_RE.sub("", before).strip()
        return key, after.strip()
    return _KEY_PREFIX_RE.sub("", raw).strip(), ""


def _meta_line(plan: dict) -> str:
    teacher = plan.get("teacher") or "____"
    teaching_object = plan.get("teachingObject") or "____"
    return (
        f"{plan.get('academicYear', '')}学年 第{plan.get('semester', '')}学期  "
        f"课程：{plan.get('course', '')}  教研组：{plan.get('teachingGroup', '')}  "
        f"任课教师：{teacher}  教学对象：{teaching_object}  "
        f"第{plan.get('week')}周第{plan.get('session')}次"
    )


def _footer_xml(plan: dict) -> str:
    digest = plan_hash(plan)[:12]
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:ftr xmlns:w="{NS_W}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        f'<w:r><w:rPr><w:sz w:val="16"/></w:rPr><w:t>'
        f"校标教案 · 引擎 {ENGINE_VERSION} · 版本 {ENGINE_VERSION} · {digest} · 第 "
        f'</w:t></w:r>'
        '<w:fldSimple w:instr=" PAGE "><w:r><w:t>1</w:t></w:r></w:fldSimple>'
        '<w:r><w:t> 页</w:t></w:r></w:p></w:ftr>'
    )


def _student_with_evidence(item: dict) -> str:
    student = _activity_text(item, "studentActivity")
    evidence = _activity_text(item, "evidence")
    if evidence:
        return "\n".join(part for part in (student, f"产出：{evidence}") if part)
    return student


def _prefixed_flow_text(key: str, text: str, *, prefixed: bool) -> str:
    if not prefixed:
        return text
    heading = ACTIVITY_FLOW_LABELS.get(key, key)
    return f"**{heading}**\n{text}"


def _collect_step(
    plan: dict,
    key: str,
    *,
    keep_activity_columns: bool,
    prefixed: bool,
) -> tuple[list[str], list[dict], list[dict]]:
    value = (plan.get("activityFlow") or {}).get(key)
    assets = _assets_for(plan, f"activityFlow.{key}") + _assets_for(plan, key)
    activities = _structured_activities(value)
    if activities is None:
        if not value:
            return [], [], assets
        return [_prefixed_flow_text(key, str(value), prefixed=prefixed)], [], assets
    if keep_activity_columns:
        return [], activities, assets
    mains: list[str] = []
    for item in activities:
        main = _activity_text(item, "mainContent")
        if main:
            mains.append(_prefixed_flow_text(key, main, prefixed=prefixed))
    return mains, [], assets


def build_document_xml(plan: dict, pkg: DocxPackage) -> str:
    """Build the reference-style single table used by the supplied teaching design."""
    content = "\n".join(x for x in [plan.get("contentTitle") or "", plan.get("contentDetail") or ""] if x)
    widths = COL_WIDTHS
    full_w = sum(widths)
    rows: list[str] = []
    key_text, diff_text = _split_key_points(str(plan.get("keyPoints") or ""))

    rows.append(_row([
        _cell_xml(pkg.label_paragraph("教学内容", center=True), shade=LABEL_SHADE, span=2, width=1101, valign="center"),
        _cell_xml(_field_paras(pkg, plan, "contentTitle", content), shade=LABEL_SHADE, span=4, width=6475),
        _cell_xml(pkg.label_paragraph("课时", center=True), shade=LABEL_SHADE, width=1001, valign="center"),
        _cell_xml(pkg.render_markdown(str(plan.get("plannedHours", ""))), shade=LABEL_SHADE, width=711),
    ]))
    rows.append(_row([
        _cell_xml(pkg.label_paragraph("教学目的", center=True), shade=LABEL_SHADE, span=2, width=1101, valign="center"),
        _cell_xml(_field_paras(pkg, plan, "teachingPurpose", str(plan.get("teachingPurpose") or "")), span=6, width=8187),
    ]))
    goals = [("知识目标", "knowledgeGoals"), ("能力目标", "abilityGoals"), ("素质目标", "qualityGoals")]
    for index, (label, field) in enumerate(goals):
        rows.append(_row([
            _cell_xml(pkg.label_paragraph("教学目标" if index == 0 else "", center=True), shade=LABEL_SHADE, span=2, width=1101, vmerge="restart" if index == 0 else "continue", valign="center"),
            _cell_xml(pkg.label_paragraph(label, center=True), width=1275, valign="center"),
            _cell_xml(_field_paras(pkg, plan, field, str(plan.get(field) or "")), span=5, width=6912),
        ]))
    for label, text, field in (
        ("教学重点", key_text, "keyPoints"),
        ("教学难点", diff_text, "keyPoints"),
        ("教学方法", str(plan.get("teachingMethods") or ""), "teachingMethods"),
        ("教学准备", str(plan.get("teachingResources") or ""), "teachingResources"),
    ):
        rows.append(_row([
            _cell_xml(pkg.label_paragraph(label, center=True), shade=LABEL_SHADE, span=2, width=1101, valign="center"),
            _cell_xml(_field_paras(pkg, plan, field, text), span=6, width=8187),
        ]))

    rows.append(_row([_cell_xml(pkg.label_paragraph("教学过程", center=True), shade=HEADER_SHADE, span=8, width=full_w, valign="center")], header=True))

    groups = [
        ("课前组织", ("introduction",), False),
        ("导入新课", ("learningGoals",), False),
        ("知识学习", ("knowledgeLearning",), False),
        ("任务实施", ("taskImplementation",), True),
        ("课程考核", ("assessment",), False),
        ("课堂小结", ("summary",), False),
        ("课后作业与反思", ("homework", "reflection"), False),
    ]
    for label, keys, is_task_group in groups:
        if is_task_group:
            rows.append(_row([
                _cell_xml(pkg.label_paragraph("教学环节", center=True), shade=HEADER_SHADE, width=827, valign="center"),
                _cell_xml(pkg.label_paragraph("主要内容", center=True), shade=HEADER_SHADE, span=3, width=3534, valign="center"),
                _cell_xml(pkg.label_paragraph("教学活动", center=True), shade=HEADER_SHADE, span=4, width=4927, valign="center"),
            ], header=True))
            rows.append(_row([
                _cell_xml("", shade=HEADER_SHADE, width=827, valign="center"),
                _cell_xml("", shade=HEADER_SHADE, span=3, width=3534, valign="center"),
                _cell_xml(pkg.label_paragraph("教师活动", center=True), shade=HEADER_SHADE, width=2551, valign="center"),
                _cell_xml(pkg.label_paragraph("学生活动", center=True), shade=HEADER_SHADE, span=3, width=2376, valign="center"),
            ], header=True))

        prefixed = len(keys) > 1
        main_parts: list[str] = []
        structured_items: list[dict] = []
        assets: list[dict] = []
        nonempty_keys = [key for key in keys if (plan.get("activityFlow") or {}).get(key)]
        use_prefix = prefixed and len(nonempty_keys) > 1
        for key in keys:
            mains, items, step_assets = _collect_step(
                plan, key, keep_activity_columns=is_task_group, prefixed=use_prefix
            )
            main_parts.extend(mains)
            structured_items.extend(items)
            assets.extend(step_assets)

        if is_task_group and structured_items:
            for index, item in enumerate(structured_items):
                main_xml = pkg.render_markdown(_activity_text(item, "mainContent"))
                if index == 0:
                    for asset in assets:
                        main_xml += pkg.render_image_asset(asset)
                rows.append(_row([
                    _cell_xml(pkg.label_paragraph(_activity_label(label, item), center=True), shade=LABEL_SHADE, width=827, valign="center"),
                    _cell_xml(main_xml, span=3, width=3534),
                    _cell_xml(pkg.render_markdown(_activity_text(item, "teacherActivity")), width=2551),
                    _cell_xml(pkg.render_markdown(_student_with_evidence(item)), span=3, width=2376),
                ]))
            continue

        main_xml = pkg.render_markdown("\n\n".join(main_parts))
        for asset in assets:
            main_xml += pkg.render_image_asset(asset)
        minutes_item = next((item for item in structured_items if item.get("minutes") not in (None, "")), None)
        step_label = _activity_label(label, minutes_item) if minutes_item else label
        rows.append(_row([
            _cell_xml(pkg.label_paragraph(step_label, center=True), shade=LABEL_SHADE, width=827, valign="center"),
            _cell_xml(main_xml, span=7, width=8461),
        ]))

    table = _table_xml(rows, widths)
    title = pkg.title_paragraph(f"《{plan.get('contentTitle') or '未命名课题'}》")
    body = title + pkg.render_markdown(_meta_line(plan)) + table
    footer_ref = (
        '<w:footerReference w:type="default" r:id="rIdFooter"/>'
        if pkg.footer_xml is not None
        else ""
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{NS_W}" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<w:body>{body}'
        f'<w:sectPr>{footer_ref}<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1800" w:bottom="1440" w:left="1800"/>'
        "</w:sectPr></w:body></w:document>"
    )


def export_docx_result(
    plan: dict,
    output: Path,
    *,
    base_dir: Path | None = None,
) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    pkg = DocxPackage(base_dir=base_dir)
    pkg.footer_xml = _footer_xml(plan)
    document_xml = build_document_xml(plan, pkg)
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


def export_docx(plan: dict, output: Path, *, base_dir: Path | None = None) -> Path:
    return export_docx_result(plan, output, base_dir=base_dir)["path"]


def self_check(output: Path, plan: dict, media: list[dict] | None = None) -> dict:
    media = media or []
    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
        document = zf.read("word/document.xml").decode("utf-8") if "word/document.xml" in names else ""
        footer = zf.read("word/footer1.xml").decode("utf-8") if "word/footer1.xml" in names else ""
        title = str(plan.get("contentTitle") or "未命名课题")
        checks = {
            "document": bool(document),
            "footer": bool(footer),
            "pageField": 'w:instr=" PAGE "' in footer,
            "engine": ENGINE_VERSION in footer,
            "planHash": plan_hash(plan)[:12] in footer,
            "title": title in document or title.replace("&", "&amp;") in document,
            "media": True,
        }
        media_details = []
        for item in media:
            dest = item["dest"]
            if dest not in names:
                media_details.append({"dest": dest, "ok": False, "reason": "missing"})
                checks["media"] = False
                continue
            digest = hashlib.sha256(zf.read(dest)).hexdigest()
            ok = digest == item.get("sha256")
            media_details.append({"dest": dest, "ok": ok, "sha256": digest})
            if not ok:
                checks["media"] = False
    return {"ok": all(checks.values()), "checks": checks, "media": media_details}


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
    result = export_docx_result(plan, out, base_dir=plan_path.parent)
    check = self_check(Path(result["path"]), plan, result["media"])
    if not check["ok"]:
        print(
            dump({"ok": False, "reasons": ["导出后自检未通过"], "selfCheck": check}),
            file=sys.stderr,
        )
        return 1
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
    sys.exit(main())
