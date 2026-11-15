# -*- coding: utf-8 -*-
"""OPS-02/03：快照 manifest、恢复与失败回滚。"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import backup_data  # noqa: E402
import restore_data  # noqa: E402


class TestBackupRestore(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.gettempdir()) / f"lpp-ops-{uuid.uuid4().hex}"
        self.root.mkdir(mode=0o777)
        self.data = self.root / "data"
        self.data.mkdir()
        self._make_database(self.data / "app.db")
        (self.data / "files").mkdir()
        (self.data / "files" / "plan-1.json").write_text('{"ok": true}\n', encoding="utf-8")
        (self.data / "exports").mkdir()
        (self.data / "exports" / "plan-1.docx").write_bytes(b"docx-bytes")
        self.backups = self.root / "backups"

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _make_database(self, path: Path) -> None:
        connection = sqlite3.connect(path)
        try:
            connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
            connection.execute("INSERT INTO sample (name) VALUES ('one'), ('two')")
            connection.execute("CREATE TABLE plan (id INTEGER PRIMARY KEY, title TEXT)")
            connection.execute("INSERT INTO plan (title) VALUES ('教案')")
            connection.execute("PRAGMA user_version=13")
            connection.commit()
        finally:
            connection.close()

    def test_snapshot_manifest_matches_files_and_zip(self) -> None:
        payload = backup_data.create_snapshot(self.data, self.backups, label="unit", make_zip=True)
        snapshot = Path(str(payload["path"]))
        manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["formatVersion"], 1)
        self.assertEqual(manifest["schemaVersion"], 13)
        self.assertEqual(manifest["database"]["rowCounts"], {"plan": 1, "sample": 2})
        self.assertEqual(manifest["database"]["integrity"], "ok")
        paths = {str(item["path"]) for item in manifest["files"]}
        self.assertTrue({"app.db", "files/plan-1.json", "exports/plan-1.docx"} <= paths)
        for item in manifest["files"]:
            self.assertEqual(backup_data.sha256_file(snapshot / item["path"]), item["sha256"])
        zip_path = Path(str(payload["zip"]))
        with zipfile.ZipFile(zip_path) as archive:
            self.assertIn("manifest.json", archive.namelist())
            self.assertIn("app.db", archive.namelist())

    def test_restore_to_new_target(self) -> None:
        payload = backup_data.create_snapshot(self.data, self.backups)
        target = self.root / "restored"
        report = restore_data.restore_snapshot(Path(str(payload["path"])), target)
        self.assertTrue(report["ok"])
        self.assertEqual(report["rowCounts"], {"plan": 1, "sample": 2})
        self.assertEqual((target / "files" / "plan-1.json").read_text(encoding="utf-8"), '{"ok": true}\n')
        self.assertEqual((target / "exports" / "plan-1.docx").read_bytes(), b"docx-bytes")

    def test_tampered_snapshot_is_rejected_without_touching_target(self) -> None:
        payload = backup_data.create_snapshot(self.data, self.backups)
        snapshot = Path(str(payload["path"]))
        (snapshot / "files" / "plan-1.json").write_text('{"ok": false}\n', encoding="utf-8")
        target = self.root / "restored"
        with self.assertRaises(restore_data.RestoreError) as caught:
            restore_data.restore_snapshot(snapshot, target)
        self.assertEqual(caught.exception.code, 3)
        self.assertFalse(target.exists())

    def test_nonempty_target_requires_force_and_keeps_backup(self) -> None:
        payload = backup_data.create_snapshot(self.data, self.backups)
        target = self.root / "restored"
        target.mkdir()
        (target / "old.txt").write_text("old", encoding="utf-8")
        with self.assertRaises(restore_data.RestoreError) as caught:
            restore_data.restore_snapshot(Path(str(payload["path"])), target)
        self.assertEqual(caught.exception.code, 3)
        report = restore_data.restore_snapshot(Path(str(payload["path"])), target, force=True)
        self.assertTrue(Path(report["backup"]).is_dir())
        self.assertTrue((Path(report["backup"]) / "old.txt").is_file())
        self.assertFalse((target / "old.txt").exists())

    def test_future_schema_is_rejected(self) -> None:
        payload = backup_data.create_snapshot(self.data, self.backups)
        snapshot = Path(str(payload["path"]))
        manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
        manifest["schemaVersion"] = 99
        (snapshot / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        with self.assertRaises(restore_data.RestoreError) as caught:
            restore_data.verify_snapshot(snapshot)
        self.assertEqual(caught.exception.code, 4)


if __name__ == "__main__":
    unittest.main()
