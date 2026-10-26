# -*- coding: utf-8 -*-
"""把需求文档 Markdown 渲染为可提交的 Word。

用法：
    python scripts/build_requirements_docx.py
    python scripts/build_requirements_docx.py --src 某文档.md --out 某文档.docx

只支持本项目文档用到的 Markdown 子集：一至四级标题、段落、无序/有序列表、
管道表格、行内加粗与行内代码、链接文本、<!-- pagebreak --> 分页标记。
依赖 python-docx；系统 Python 未安装该库时，改用已安装它的解释器执行。
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
BODY_FONT = "宋体"
HEAD_FONT = "黑体"
ASCII_FONT = "Times New Roman"
CODE_FONT = "Consolas"

INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")
TABLE_SEPARATOR_RE = re.compile(r"^\|[\s:\-|]+\|$")
ORDERED_RE = re.compile(r"^\d+\.\s+")

COLUMN_WIDTHS_CM: dict[tuple[str, ...], list[float]] = {
    ("项目", "内容"): [4.2, 11.6],
    ("术语", "含义"): [4.0, 11.8],
    ("角色", "职责", "备注"): [3.2, 8.4, 4.2],
    ("用户任务", "现状阻碍", "对应需求"): [6.6, 6.6, 2.6],
    ("阶段", "教师动作", "系统现状", "主要断点"): [2.2, 4.2, 4.2, 5.2],
    ("编号", "缺陷描述", "严重度", "证据"): [1.6, 6.4, 1.8, 6.0],
    ("目标", "对应研究问题", "基线（2026-10-25）", "目标值"): [3.0, 3.8, 4.8, 4.2],
    ("编号", "需求名称", "优先级", "对应缺陷", "关联目标"): [1.6, 4.4, 1.8, 3.6, 4.4],
    ("编号", "需求", "验收口径"): [1.6, 3.4, 10.8],
    ("层级", "对象", "主要手段"): [1.8, 4.6, 9.4],
    ("需求组", "用例类型", "目标条数"): [7.4, 4.2, 4.2],
    ("维度", "取值"): [3.0, 12.8],
    ("缺陷", "回归用例", "判定"): [2.2, 4.4, 9.2],
    ("时间", "里程碑", "交付", "覆盖需求"): [2.2, 3.4, 6.8, 3.4],
    ("时间", "阶段", "交付", "覆盖需求"): [2.2, 3.4, 6.8, 3.4],
    ("风险", "影响", "应对"): [4.8, 3.2, 7.8],
    ("编号", "复现方式", "观测结果"): [1.6, 6.4, 7.8],
    ("开题指标", "支撑需求", "说明"): [3.2, 4.2, 8.4],
    ("需求", "缺陷", "优先级", "主要验收证据"): [1.6, 3.2, 1.6, 9.4],
    ("能力", "插件/技能端", "平台端"): [3.2, 6.0, 6.6],
    ("编号", "需求名称", "优先级", "关联契约", "验收指标"): [1.6, 4.2, 1.8, 3.4, 4.8],
    ("页面", "角色", "核心操作", "空态与异常"): [2.6, 2.2, 5.4, 5.6],
    ("方法", "路径", "角色", "说明", "幂等"): [1.9, 4.8, 2.2, 5.0, 1.9],
    ("实体", "关键字段", "约束"): [2.4, 7.4, 6.0],
    ("对象", "关键字段", "平台端处理"): [2.4, 6.4, 7.0],
    ("插件端需求", "平台端依赖", "验收方式"): [3.0, 6.6, 6.2],
    ("编号", "检查项", "通过标准"): [1.6, 6.2, 8.0],
    ("现状项", "证据", "影响"): [3.4, 5.6, 6.8],
    ("需求组", "测试类型", "目标条数"): [7.4, 4.2, 4.2],
    ("错误码", "含义", "使用场景"): [4.2, 4.4, 7.2],
    ("决策", "理由", "影响"): [4.2, 6.0, 5.6],
    ("能力", "插件端", "平台端", "交接物"): [3.0, 4.0, 4.2, 4.6],
    ("事项", "负责", "审批/验收", "协作", "产出"): [3.0, 3.0, 3.4, 3.0, 3.4],
    ("需求组", "编号范围", "所属端", "负责", "验收", "里程碑"): [2.6, 4.4, 2.0, 1.8, 1.8, 3.2],
    ("时间", "交接内容", "从", "到", "验收物"): [1.8, 4.4, 1.6, 1.6, 6.4],
    ("环节", "触发", "动作", "产出"): [2.6, 3.6, 6.2, 3.4],
    ("分支", "用途", "合并方式"): [3.4, 6.4, 6.0],
}


def smart_quotes(text: str) -> str:
    """把中文段落里的成对半角引号换成全角，代码片段不会走到这里。"""
    result: list[str] = []
    opening = True
    for char in text:
        if char == '"':
            result.append("\u201c" if opening else "\u201d")
            opening = not opening
        else:
            result.append(char)
    return "".join(result)


def set_run_font(
    run,
    *,
    font: str = BODY_FONT,
    size: float = 12,
    bold: bool | None = None,
    color: RGBColor | None = None,
) -> None:
    run.font.name = ASCII_FONT if font != CODE_FONT else CODE_FONT
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), ASCII_FONT if font != CODE_FONT else CODE_FONT)
    rfonts.set(qn("w:hAnsi"), ASCII_FONT if font != CODE_FONT else CODE_FONT)
    rfonts.set(qn("w:eastAsia"), font)


def set_style_font(style, *, east_asia: str, ascii_font: str, size: float, bold: bool) -> None:
    style.font.name = ascii_font
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), ascii_font)
    rfonts.set(qn("w:hAnsi"), ascii_font)
    rfonts.set(qn("w:eastAsia"), east_asia)


def add_inline(paragraph, text: str, *, size: float = 12, bold: bool = False) -> None:
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            run = paragraph.add_run(smart_quotes(part[2:-2]))
            set_run_font(run, size=size, bold=True)
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            run = paragraph.add_run(part[1:-1])
            set_run_font(run, font=CODE_FONT, size=max(size - 1, 8), bold=bold)
        elif part.startswith("[") and "](" in part:
            run = paragraph.add_run(smart_quotes(part[1 : part.index("]")]))
            set_run_font(run, size=size, bold=bold)
        else:
            run = paragraph.add_run(smart_quotes(part))
            set_run_font(run, size=size, bold=bold)


def shade_cell(cell, fill: str = "F2F2F2") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def add_field(paragraph, instruction: str, placeholder: str = "1") -> None:
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), f" {instruction} ")
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = placeholder
    run.append(text)
    field.append(run)
    paragraph._p.append(field)


def plain_markup(text: str) -> str:
    return text.replace("**", "").replace("`", "").strip()


def add_table(document: Document, rows: list[list[str]]) -> None:
    cols = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    widths = COLUMN_WIDTHS_CM.get(tuple(plain_markup(cell) for cell in rows[0]))
    headers = [plain_markup(cell) for cell in rows[0]]
    centered = {index for index, name in enumerate(headers) if name in {"优先级", "严重度", "目标条数"}}
    code_table = bool(headers) and headers[0] == "错误码"
    if widths and len(widths) == cols:
        table.autofit = False
        for index, width in enumerate(widths):
            table.columns[index].width = Cm(width)
    for r_index, row in enumerate(rows):
        for c_index in range(cols):
            cell = table.cell(r_index, c_index)
            if widths and len(widths) == cols:
                cell.width = Cm(widths[c_index])
            text = row[c_index] if c_index < len(row) else ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_before = Pt(1)
            paragraph.paragraph_format.space_after = Pt(1)
            paragraph.paragraph_format.line_spacing = 1.15
            if c_index in centered:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cell_size = 9 if (code_table and c_index == 0 and r_index > 0) else 10
            add_inline(paragraph, text, size=cell_size, bold=(r_index == 0))
            if r_index == 0:
                shade_cell(cell)
    header_tr = table.rows[0]._tr
    tr_pr = header_tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))
    document.add_paragraph().paragraph_format.space_after = Pt(2)


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        raw = lines[index].strip()
        if not TABLE_SEPARATOR_RE.match(raw):
            cells = [cell.strip() for cell in raw.strip("|").split("|")]
            rows.append(cells)
        index += 1
    return rows, index


def build(markdown_path: Path, output_path: Path) -> Path:
    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    title = ""
    subtitle = ""
    for index, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            for follow in lines[index + 1 : index + 6]:
                stripped = follow.strip()
                if stripped.startswith("**") and stripped.endswith("**"):
                    subtitle = stripped[2:-2].strip()
                    break
            break
    header_text = title or "需求说明书"
    version_match = re.search(r"v\d+\.\d+", subtitle)
    if version_match:
        header_text = f"{header_text} · {version_match.group(0)}"

    document = Document()

    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.4)
    section.left_margin = Cm(2.7)
    section.right_margin = Cm(2.5)
    section.different_first_page_header_footer = True

    normal = document.styles["Normal"]
    set_style_font(normal, east_asia=BODY_FONT, ascii_font=ASCII_FONT, size=12, bold=False)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)

    heading_specs = [
        ("Heading 1", 16, 14, 8),
        ("Heading 2", 14, 12, 6),
        ("Heading 3", 13, 10, 4),
        ("Heading 4", 12, 8, 3),
    ]
    for name, size, before, after in heading_specs:
        style = document.styles[name]
        set_style_font(style, east_asia=HEAD_FONT, ascii_font=ASCII_FONT, size=size, bold=True)
        style.font.italic = False
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_run = header.add_run(header_text)
    set_run_font(header_run, size=9, color=RGBColor(0x66, 0x66, 0x66))

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    label = footer.add_run("第 ")
    set_run_font(label, size=9)
    add_field(footer, "PAGE")
    middle = footer.add_run(" 页 / 共 ")
    set_run_font(middle, size=9)
    add_field(footer, "NUMPAGES", "1")
    tail = footer.add_run(" 页")
    set_run_font(tail, size=9)

    title_done = False
    expect_subtitle = False
    index = 0
    while index < len(lines):
        raw = lines[index]
        line = raw.strip()
        if not line:
            index += 1
            continue
        if line == "<!-- pagebreak -->":
            document.add_page_break()
            index += 1
            continue
        if line.startswith("|"):
            rows, index = parse_table(lines, index)
            if rows:
                add_table(document, rows)
            continue
        heading_match = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            if level == 1 and not title_done:
                paragraph = document.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.space_before = Pt(150)
                paragraph.paragraph_format.space_after = Pt(18)
                run = paragraph.add_run(text)
                set_run_font(run, font=HEAD_FONT, size=24, bold=True)
                title_done = True
                expect_subtitle = True
            else:
                document.add_heading(text, level=level)
                expect_subtitle = False
            index += 1
            continue
        if expect_subtitle and re.fullmatch(r"\*\*[^*]+\*\*", line):
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(36)
            run = paragraph.add_run(line[2:-2])
            set_run_font(run, font=HEAD_FONT, size=14, bold=False)
            expect_subtitle = False
            index += 1
            continue
        expect_subtitle = False
        if line.startswith("- "):
            paragraph = document.add_paragraph(style="List Bullet")
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_inline(paragraph, line[2:], size=12)
        elif ORDERED_RE.match(line):
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Cm(0.75)
            paragraph.paragraph_format.first_line_indent = Cm(-0.75)
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_inline(paragraph, line, size=12)
        elif line.startswith(">"):
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Cm(0.75)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_inline(paragraph, line.lstrip("> ").strip(), size=11)
        else:
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_inline(paragraph, line, size=12)
        index += 1

    properties = document.core_properties
    properties.title = title or "需求说明书"
    properties.subject = subtitle or "需求说明书"
    properties.author = "毕业设计"
    properties.comments = "需求说明书"
    properties.category = "需求说明书"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="把需求文档 Markdown 渲染为 DOCX")
    parser.add_argument("--src", default=str(ROOT / "功能优化需求-校标教案生成平台.md"))
    parser.add_argument("--out", default=str(ROOT / "功能优化需求-校标教案生成平台.docx"))
    args = parser.parse_args()
    saved = build(Path(args.src), Path(args.out))
    print(f"saved {saved} ({saved.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

