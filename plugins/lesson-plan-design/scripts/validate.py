# -*- coding: utf-8 -*-
"""插件根入口：转发到技能内 validate.py。"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import skill_scripts

if __name__ == "__main__":
    target = skill_scripts() / "validate.py"
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")
