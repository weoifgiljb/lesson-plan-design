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


    def test_run_snapshot_is_eligible_for_retention(self) -> None:
        # 回归：快照目录名是 `<UTC时间戳>-auto-...`，旧的 startswith("auto-") 过滤永远匹配不到自己
        data = self.root / "data"
        data.mkdir()
        sqlite3.connect(data / "app.db").close()
        backups = self.root / "backups"
        first = auto_backup.run(data, backups, keep=1, weekly_keep=1, make_zip=True)
        first_path = Path(first["snapshot"])
        self.assertIn(first_path.name, [path.name for path, _ in auto_backup.auto_snapshots(backups)])
        self.assertTrue(auto_backup.zip_path_for(first_path).exists())

        # 把第一份改成两天前，再跑一次 keep=1：旧快照与 zip 必须被删
        manifest_path = first_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["createdAt"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        second = auto_backup.run(data, backups, keep=1, weekly_keep=0, make_zip=True)
        remaining = {path.name for path, _ in auto_backup.auto_snapshots(backups)}
        self.assertIn(Path(second["snapshot"]).name, remaining)
        self.assertNotIn(first_path.name, remaining)
        self.assertFalse(first_path.exists())
        self.assertFalse(auto_backup.zip_path_for(first_path).exists())


if __name__ == "__main__":
    unittest.main()
