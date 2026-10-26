# -*- coding: utf-8 -*-
"""兼容门面：域实现见 lesson_plan，旧调用保持 from lib import ... 不变。"""
from __future__ import annotations

from lesson_plan.draft import draft_plan
from lesson_plan.examples import check_examples, example_entries, load_examples
from lesson_plan.gate import (
    _refresh_report_status,
    derive_review_status,
    export_gate,
    record_teacher_override,
)
from lesson_plan.jsonio import dump, load_json
from lesson_plan.model import (
    ACTIVITY_FLOW_LABELS,
    BLOCKING_SEVERITIES,
    C_LANGUAGE_TEMPLATES_PATH,
    EXAMPLES_DIR,
    EXAMPLES_INDEX,
    KNOWLEDGE_A,
    KNOWLEDGE_B,
    MIN_OVERRIDE_REASON,
    REQUIRED_FLOW,
    REQUIRED_TOP,
    REVIEW_SCHEMA_VERSION,
    RUBRIC_VERSION,
    RULES_VERSION,
    SCHOOL_DEFAULTS,
    SKILL_DIR,
    TEMPLATES_DIR,
    TOOL_VERSION,
    _activity_minutes,
    _finalize_findings,
    _nonempty,
    _normalise_text,
    _structured_activities,
    _structured_task_text,
    empty_flow,
    empty_plan,
    plan_hash,
)
from lesson_plan.review import adversarial_review
from lesson_plan.review_store import (
    default_review_path,
    load_review_report,
    save_review_report,
)
from lesson_plan.scoring import overlap_ratio, score_against_examples, tokenize
from lesson_plan.validation import validate_plan

__all__ = [
    "ACTIVITY_FLOW_LABELS", "BLOCKING_SEVERITIES", "C_LANGUAGE_TEMPLATES_PATH",
    "EXAMPLES_DIR", "EXAMPLES_INDEX", "KNOWLEDGE_A", "KNOWLEDGE_B",
    "MIN_OVERRIDE_REASON", "REQUIRED_FLOW", "REQUIRED_TOP", "REVIEW_SCHEMA_VERSION",
    "RUBRIC_VERSION", "RULES_VERSION", "SCHOOL_DEFAULTS", "SKILL_DIR",
    "TEMPLATES_DIR", "TOOL_VERSION", "adversarial_review", "check_examples",
    "default_review_path", "derive_review_status", "draft_plan", "dump",
    "empty_flow", "empty_plan", "example_entries", "export_gate", "load_examples",
    "load_json", "load_review_report", "overlap_ratio", "plan_hash",
    "record_teacher_override", "save_review_report", "score_against_examples",
    "tokenize", "validate_plan",
]
