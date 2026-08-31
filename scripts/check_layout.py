# -*- coding: utf-8 -*-
"""对照计划验收插件目录是否齐备。"""
from __future__ import annotations

import sys
from pathlib import Path

# This script lives in <repo>/scripts/, while the plugin lives in <repo>/plugins/.
ROOT = Path(__file__).resolve().parent.parent / "plugins" / "lesson-plan-design"
REQUIRED = [
    ".codex-plugin/plugin.json",
    ".qoder-plugin/plugin.json",
    ".codebuddy-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
    "AGENTS.md",
    "RULES.md",
    "commands/write-lesson-plan.md",
    "commands/validate-lesson-plan.md",
    "agents/lesson-plan-reviewer.md",
    "hooks/hooks.json",
    "scripts/session-start.py",
    "scripts/validate.py",
    "scripts/export_docx.py",
    "scripts/mcp_server.py",
    ".mcp.json",
    "skills/lesson-plan-design/SKILL.md",
    "skills/lesson-plan-design/RULES.md",
    "skills/lesson-plan-design/CATALOG.md",
    "skills/lesson-plan-design/references/schema.md",
    "skills/lesson-plan-design/references/validation.md",
    "skills/lesson-plan-design/templates/empty-plan.json",
    "skills/lesson-plan-design/scripts/validate.py",
    "skills/lesson-plan-design/scripts/export_docx.py",
    "skills/lesson-plan-design/examples/信息技术0102.json",
    "skills/lesson-plan-design/examples/信息技术0201.json",
    "skills/lesson-plan-design/examples/信息技术0202.json",
    "skills/lesson-plan-design/examples/信息技术0301.json",
    "skills/lesson-plan-design/examples/信息技术0302.json",
    "skills/lesson-plan-design/examples/信息技术0401.json",
    "skills/lesson-plan-design/examples/信息技术0402.json",
]


def main() -> int:
    missing = [rel for rel in REQUIRED if not (ROOT / rel).is_file()]
    if missing:
        print("MISSING:")
        for item in missing:
            print(" ", item)
        return 1
    print("layout ok", len(REQUIRED), "files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
