# -*- coding: utf-8 -*-
"""SessionStart：向宿主注入校标闸门说明。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import plugin_root

TEXT = (
    "已启用校标教案插件 lesson-plan-design。"
    "写教案必须走技能流程，导出前运行 skills/lesson-plan-design/scripts/validate.py。"
    f"插件根：{plugin_root()}"
)


def main() -> int:
    # Claude/CodeBuddy additionalContext；Codex 会收录 stdout
    payload = {
        "additionalContext": TEXT,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": TEXT,
        },
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
