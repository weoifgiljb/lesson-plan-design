# -*- coding: utf-8 -*-
"""定位技能内脚本目录。"""
from __future__ import annotations

import os
from pathlib import Path


def plugin_root() -> Path:
    env = os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def skill_scripts() -> Path:
    return plugin_root() / "skills" / "lesson-plan-design" / "scripts"
