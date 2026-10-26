# -*- coding: utf-8 -*-
"""DOCX 表格 XML 布局。"""
from __future__ import annotations

LABEL_SHADE = "E7E7E7"
HEADER_SHADE = "D9D9D9"
COL_WIDTHS = [827, 274, 1275, 1985, 2551, 664, 1001, 711]


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
