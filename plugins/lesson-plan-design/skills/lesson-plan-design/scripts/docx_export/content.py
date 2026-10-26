# -*- coding: utf-8 -*-
"""DOCX 内容渲染：媒体、活动行、重难点。"""
from __future__ import annotations

import re

from lib import ACTIVITY_FLOW_LABELS
from markdown_ooxml import DocxPackage

_KEY_DIFF_RE = re.compile(r"难点[:：]")
_KEY_PREFIX_RE = re.compile(r"^重点[:：]\s*")


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
