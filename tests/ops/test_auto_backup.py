# -*- coding: utf-8 -*-
"""OPS-07：自动快照与 7 日/4 周保留。"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import auto_backup  # noqa: E402
import export_contracts  # noqa: E402


def _snapshot(root: Path, label: str, created: datetime) -> Path:
    path = root / f"{label}"
    path.mkdir()
    (path / "manifest.json").write_text(
        json.dumps({"label": label, "createdAt": created.isoformat()}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


class TestAutoBackup(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.gettempdir()) / f"lpp-auto-backup-{uuid.uuid4().hex}"
        self.root.mkdir(mode=0o777)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_retention_keeps_daily_and_weekly_but_not_manual(self) -> None:
        now = datetime.now(timezone.utc)
        for day in range(10):
            _snapshot(self.root, f"auto-{day:02d}", now - timedelta(days=day))
        manual = _snapshot(self.root, "before-upgrade", now - timedelta(days=30))
        removed = auto_backup.apply_retention(self.root, keep=3, weekly_keep=2)
        self.assertTrue(manual.is_dir())
        self.assertTrue((self.root / "auto-00").is_dir())
        self.assertTrue((self.root / "auto-01").is_dir())
        self.assertTrue((self.root / "auto-02").is_dir())
        self.assertGreaterEqual(len(removed), 1)

    def test_contract_bundle_contains_all_three_files(self) -> None:
        output = self.root / "contracts.zip"
        export_contracts.export_contracts(Path(__file__).resolve().parents[2], output)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {"docs/api/contract.v1.json", "docs/api/openapi.v1.json", "src/frontend/src/api/types.gen.ts"},
            )

    def test_run_creates_snapshot(self) -> None:
        data = self.root / "data"
        data.mkdir()
        sqlite3.connect(data / "app.db").close()
        backups = self.root / "backups"
        payload = auto_backup.run(data, backups, keep=7, weekly_keep=4, make_zip=False)
        self.assertTrue(payload["ok"])
        self.assertTrue(Path(payload["snapshot"]).is_dir())


if __name__ == "__main__":
    unittest.main()
