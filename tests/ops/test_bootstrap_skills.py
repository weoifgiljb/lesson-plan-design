# -*- coding: utf-8 -*-
"""OPS-01：按锁文件安装、检查与离线失败路径。"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import bootstrap_skills  # noqa: E402


class TestBootstrapSkills(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.gettempdir()) / f"lpp-bootstrap-{uuid.uuid4().hex}"
        self.root.mkdir(mode=0o777)
        self.source = self.root / "source"
        (self.source / "skills" / "alpha").mkdir(parents=True)
        (self.source / "skills" / "beta").mkdir(parents=True)
        (self.source / "skills" / "alpha" / "SKILL.md").write_text("# alpha\n", encoding="utf-8")
        (self.source / "skills" / "beta" / "SKILL.md").write_text("# beta\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.source), "commit", "-qm", "fixture"], check=True)
        self.commit = subprocess.run(
            ["git", "-C", str(self.source), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.lock = self.root / "skills.lock.json"
        self.lock.write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "repo": str(self.source),
                            "commit": self.commit,
                            "sourcePath": "skills/",
                            "skills": ["alpha", "beta"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        # git 产物是只读的，Windows 上 rmtree 会卡住，先去掉只读位再删
        def _on_error(func, path, _exc) -> None:
            os.chmod(path, stat.S_IWRITE)
            func(path)

        shutil.rmtree(self.root, onexc=_on_error)

    def _prepare_cache(self, cache: Path) -> None:
        target = bootstrap_skills._cache_dir(cache, str(self.source))
        shutil.copytree(self.source, target)

    def test_install_then_check(self) -> None:
        target = self.root / "installed"
        cache = self.root / "cache"
        self._prepare_cache(cache)
        payload = bootstrap_skills.install(
            self.lock, target, cache=cache, offline=True
        )
        self.assertEqual(payload["count"], 2)
        self.assertTrue((target / "alpha" / "SKILL.md").is_file())
        self.assertTrue((target / ".installed.json").is_file())
        checked = bootstrap_skills.check(self.lock, target)
        self.assertTrue(checked["ok"], checked["errors"])

    def test_hash_mismatch_is_reported(self) -> None:
        target = self.root / "installed"
        cache = self.root / "cache"
        self._prepare_cache(cache)
        bootstrap_skills.install(self.lock, target, cache=cache, offline=True)
        (target / "alpha" / "SKILL.md").write_text("# changed\n", encoding="utf-8")
        checked = bootstrap_skills.check(self.lock, target)
        self.assertFalse(checked["ok"])
        self.assertIn("哈希不一致", "；".join(checked["errors"]))

    def test_offline_without_cache_fails_with_code_4(self) -> None:
        with self.assertRaises(bootstrap_skills.BootstrapError) as caught:
            bootstrap_skills.install(
                self.lock,
                self.root / "installed",
                cache=self.root / "empty-cache",
                offline=True,
            )
        self.assertEqual(caught.exception.code, 4)


if __name__ == "__main__":
    unittest.main()
