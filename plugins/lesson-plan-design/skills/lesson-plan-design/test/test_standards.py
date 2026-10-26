# -*- coding: utf-8 -*-
"""代码规范文件与入口契约。"""
from __future__ import annotations

import unittest
from pathlib import Path

from support import SKILL_DIR

ROOT = SKILL_DIR.parents[3]
RULE = ROOT / ".cursor" / "rules" / "code-standards.mdc"
SKILL = ROOT / "skills" / "code-standards" / "SKILL.md"
AGENTS = ROOT / "AGENTS.md"
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"


class TestStandards(unittest.TestCase):
    def test_rule_and_skill_exist(self) -> None:
        self.assertTrue(RULE.is_file(), RULE)
        self.assertTrue(SKILL.is_file(), SKILL)
        rule = RULE.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")
        for term in ("alwaysApply: true", "绝对路径", "映射", "derive_review_status"):
            self.assertIn(term, rule)
        for term in ("工作流", "组件地图", "检查清单", "derive_review_status"):
            self.assertIn(term, skill)

    def test_agents_and_pr_template_reference_rules(self) -> None:
        agents = AGENTS.read_text(encoding="utf-8")
        template = PR_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("skills/code-standards/SKILL.md", agents)
        self.assertIn("derive_review_status", agents)
        self.assertIn("代码组织", template)
        self.assertIn("全量 runner", template)
