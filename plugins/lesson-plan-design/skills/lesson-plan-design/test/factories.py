# -*- coding: utf-8 -*-
"""测试夹具：教案、报告与 CLI 子进程。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from support import SCRIPTS_DIR, utf8_env
from lib import (
    adversarial_review,
    default_review_path,
    draft_plan,
    save_review_report,
)


def make_plan(week: int = 1, session: int = 1, title: str = "测试课题", **kwargs) -> dict:
    return draft_plan(week, session, title, **kwargs)


def write_plan(root: Path, plan: dict, name: str = "教案.json") -> Path:
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return path


def write_report(
    plan_path: Path,
    plan: dict,
    *,
    reviewer: str = "native_subagent",
    no_counterexample: bool = True,
) -> dict:
    report = adversarial_review(
        plan,
        reviewer=reviewer,
        no_counterexample=no_counterexample,
    )
    save_review_report(default_review_path(plan_path), report)
    return report


def run_cli(script: str, *args, input_text: str | None = None) -> subprocess.CompletedProcess:
    command = [sys.executable, str(SCRIPTS_DIR / script), *(str(item) for item in args)]
    return subprocess.run(
        command,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=utf8_env(),
    )


def read_docx_xml(path: Path) -> str:
    import zipfile

    with zipfile.ZipFile(path) as archive:
        return archive.read("word/document.xml").decode("utf-8")
