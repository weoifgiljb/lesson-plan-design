# -*- coding: utf-8 -*-
"""写教案流程文档契约。"""
from __future__ import annotations

import unittest

from support import PLUGIN_ROOT, SKILL_DIR


class TestDocs(unittest.TestCase):
    def test_write_flow_docs_require_finding_or_attestation(self) -> None:
        skill = SKILL_DIR / "SKILL.md"
        write_cmd = PLUGIN_ROOT / "commands" / "write-lesson-plan.md"
        skill_text = skill.read_text(encoding="utf-8")
        write_text = write_cmd.read_text(encoding="utf-8")
        self.assertIn("--finding", skill_text)
        self.assertIn("--no-counterexample", skill_text)
        self.assertIn("--finding", write_text)
        self.assertIn("--no-counterexample", write_text)

    def test_write_flow_docs_mention_markdown_and_media_assets(self) -> None:
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        schema_text = (SKILL_DIR / "references" / "schema.md").read_text(encoding="utf-8")
        readme_text = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("mediaAssets", skill_text)
        self.assertIn("Markdown", skill_text)
        self.assertIn("formatting-lesson-docx", skill_text)
        self.assertIn("mediaAssets", schema_text)
        self.assertIn("capturing-ebook-pages", readme_text)
        self.assertIn("formatting-lesson-docx", readme_text)
        write_text = (PLUGIN_ROOT / "commands" / "write-lesson-plan.md").read_text(encoding="utf-8")
        self.assertIn("mediaAssets", write_text)
        self.assertIn("Markdown", write_text)

    def test_qc_goal_and_keypoint_writing_rules(self) -> None:
        rules = (SKILL_DIR / "RULES.md").read_text(encoding="utf-8")
        agents = (PLUGIN_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        schema = (SKILL_DIR / "references" / "schema.md").read_text(encoding="utf-8")
        reviewer = (PLUGIN_ROOT / "agents" / "lesson-plan-reviewer.md").read_text(encoding="utf-8")
        for text in (rules, agents, schema, reviewer):
            self.assertIn("可评可测", text)
            self.assertIn("学生会什么", text)
            self.assertIn("重点由", text)
            self.assertIn("教学内容", text)
            self.assertIn("难点", text)
            self.assertIn("学情", text)
