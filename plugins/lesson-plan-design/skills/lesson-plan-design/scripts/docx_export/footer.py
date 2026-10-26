# -*- coding: utf-8 -*-
"""DOCX 页脚：页码、引擎版本、planHash。"""
from __future__ import annotations

from lib import plan_hash
from markdown_ooxml import NS_W

ENGINE_VERSION = "1.0.0"


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
