# -*- coding: utf-8 -*-
"""DOCX 导出后自检。"""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from lib import plan_hash

from .footer import ENGINE_VERSION


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
