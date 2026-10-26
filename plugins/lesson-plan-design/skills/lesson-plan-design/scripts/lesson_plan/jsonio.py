# -*- coding: utf-8 -*-
"""JSON 读写。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
