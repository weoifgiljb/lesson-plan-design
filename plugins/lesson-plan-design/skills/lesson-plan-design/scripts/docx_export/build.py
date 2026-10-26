# -*- coding: utf-8 -*-
"""DOCX 文档 XML 编排。"""
from __future__ import annotations

from lib import ACTIVITY_FLOW_LABELS
from markdown_ooxml import DocxPackage, NS_W

from .content import (
    _activity_label,
    _activity_text,
    _collect_step,
    _field_paras,
    _split_key_points,
    _student_with_evidence,
)
from .layout import COL_WIDTHS, HEADER_SHADE, LABEL_SHADE, _cell_xml, _row, _table_xml
from .metadata import _format_hours, _meta_line


def build_document_xml(plan: dict, pkg: DocxPackage, *, independence: str | None = None) -> str:
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
        _cell_xml(pkg.render_markdown(_format_hours(plan.get("plannedHours"))), shade=LABEL_SHADE, width=711),
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
    body = title + pkg.render_markdown(_meta_line(plan, independence)) + table
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
