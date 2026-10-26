# -*- coding: utf-8 -*-
"""闸门自测：干净树必须绿，逐条植入违规必须被点名。

测试直接调用各闸门的 ``scan()``，不依赖 FastAPI 与网络。
"""
from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import unittest

from support import CLEAN_FILES, CONTRACT, FRONTEND_FILES, ROOT, contract_path, make_project, openapi_path, tempdir

import check_backend_architecture as arch
import check_backend_contract as contract_gate
import check_backend_security as security_gate


def blocks(problems: list[dict]) -> list[dict]:
    return [item for item in problems if item.get("severity") != "warn"]


def rules(problems: list[dict]) -> set[str]:
    return {item["rule"] for item in blocks(problems)}


def project_with(overrides: dict[str, str] | None = None, *, frontend: bool = False):
    """返回 (ExitStack, backend, frontend)；用 ``with stack:`` 收尾。"""
    stack = contextlib.ExitStack()
    root = stack.enter_context(tempdir())
    files = dict(CLEAN_FILES)
    files.update(overrides or {})
    backend, frontend_root = make_project(root, backend=files, frontend=FRONTEND_FILES if frontend else None)
    return stack, backend, frontend_root


def contract_project(*, contract: dict | None = None, routes: dict | None = None, frontend_extra: dict | None = None):
    stack = contextlib.ExitStack()
    root = stack.enter_context(tempdir())
    files = dict(FRONTEND_FILES)
    files.update(frontend_extra or {})
    backend, frontend = make_project(root, backend=dict(CLEAN_FILES), frontend=files)
    contract_file = contract_path(root, contract)
    openapi_file = openapi_path(root, routes, frontend_root=frontend)
    return stack, backend, frontend, contract_file, openapi_file


class TestArchitectureGate(unittest.TestCase):
    def test_clean_tree_has_no_blocks(self) -> None:
        stack, backend, frontend = project_with(frontend=True)
        with stack:
            self.assertEqual(blocks(arch.scan(backend, frontend)), [])

    def test_domain_import_is_blocked(self) -> None:
        stack, backend, frontend = project_with({"app/domain/bad.py": "import fastapi\n"})
        with stack:
            self.assertIn("BA-02", rules(arch.scan(backend, frontend)))

    def test_domain_print_is_blocked(self) -> None:
        stack, backend, frontend = project_with({"app/domain/bad.py": "def f() -> None:\n    print('x')\n"})
        with stack:
            self.assertIn("BA-03", rules(arch.scan(backend, frontend)))

    def test_module_too_large_is_blocked(self) -> None:
        stack, backend, frontend = project_with({"app/domain/big.py": "X = 1\n" * 400})
        with stack:
            self.assertIn("BA-07", rules(arch.scan(backend, frontend)))

    def test_except_in_domain_is_blocked(self) -> None:
        code = "def f() -> None:\n    try:\n        pass\n    except Exception:\n        pass\n"
        stack, backend, frontend = project_with({"app/domain/bad.py": code})
        with stack:
            self.assertIn("BA-09", rules(arch.scan(backend, frontend)))

    def test_unknown_error_code_is_blocked(self) -> None:
        code = "from .errors import AppError\n\n\ndef f() -> None:\n    raise AppError('NOPE')\n"
        stack, backend, frontend = project_with({"app/domain/bad.py": code})
        with stack:
            self.assertIn("BA-10", rules(arch.scan(backend, frontend)))

    def test_sys_path_outside_engine_is_blocked(self) -> None:
        stack, backend, frontend = project_with({"app/api/bad.py": "import sys\n\nsys.path.insert(0, 'x')\n"})
        with stack:
            self.assertIn("BA-11", rules(arch.scan(backend, frontend)))

    def test_missing_layer_is_blocked(self) -> None:
        files = {name: text for name, text in CLEAN_FILES.items() if not name.startswith("app/api/")}
        stack = contextlib.ExitStack()
        root = stack.enter_context(tempdir())
        backend, frontend = make_project(root, backend=files, frontend=FRONTEND_FILES)
        with stack:
            self.assertIn("BA-01", rules(arch.scan(backend, frontend)))


class TestContractGate(unittest.TestCase):
    def test_clean_contract_passes(self) -> None:
        stack, backend, frontend, contract_file, openapi_file = contract_project()
        with stack:
            self.assertEqual(blocks(contract_gate.scan(backend, frontend, contract_file, openapi_file)), [])

    def test_missing_route_is_blocked(self) -> None:
        routes = {"/api/v1/plans": ["get"]}
        stack, backend, frontend, contract_file, openapi_file = contract_project(routes=routes)
        with stack:
            self.assertIn("BC-02", rules(contract_gate.scan(backend, frontend, contract_file, openapi_file)))

    def test_extra_route_is_blocked(self) -> None:
        routes = {"/api/v1/plans": ["get"], "/api/v1/plans/import": ["post"], "/api/v1/extra": ["get"]}
        stack, backend, frontend, contract_file, openapi_file = contract_project(routes=routes)
        with stack:
            self.assertIn("BC-02", rules(contract_gate.scan(backend, frontend, contract_file, openapi_file)))

    def test_write_without_csrf_is_blocked(self) -> None:
        contract = json.loads(json.dumps(CONTRACT))
        contract["endpoints"][1]["csrf"] = False
        stack, backend, frontend, contract_file, openapi_file = contract_project(contract=contract)
        with stack:
            self.assertIn("BC-03", rules(contract_gate.scan(backend, frontend, contract_file, openapi_file)))

    def test_invalid_role_is_blocked(self) -> None:
        contract = json.loads(json.dumps(CONTRACT))
        contract["endpoints"][0]["roles"] = ["root"]
        stack, backend, frontend, contract_file, openapi_file = contract_project(contract=contract)
        with stack:
            self.assertIn("BC-04", rules(contract_gate.scan(backend, frontend, contract_file, openapi_file)))

    def test_error_code_drift_is_blocked(self) -> None:
        contract = json.loads(json.dumps(CONTRACT))
        contract["errorCodes"].append({"code": "MEDIA_MISSING", "http": 422, "zh": "媒体缺失"})
        stack, backend, frontend, contract_file, openapi_file = contract_project(contract=contract)
        with stack:
            self.assertIn("BC-05", rules(contract_gate.scan(backend, frontend, contract_file, openapi_file)))

    def test_version_drift_is_blocked(self) -> None:
        stack, backend, frontend, contract_file, openapi_file = contract_project()
        with stack:
            versions = "VERSIONS = {'schemaVersion': 2, 'rubricVersion': '1.0', 'rulesVersion': '1.1.0', 'engineVersion': '1.0.0'}\n"
            (backend / "app" / "domain" / "versions.py").write_text(versions, encoding="utf-8")
            self.assertIn("BC-06", rules(contract_gate.scan(backend, frontend, contract_file, openapi_file)))

    def test_frontend_unknown_call_is_blocked(self) -> None:
        extra = {"src/api/extra.ts": "export const x = client.get('/api/v1/nope')\n"}
        stack, backend, frontend, contract_file, openapi_file = contract_project(frontend_extra=extra)
        with stack:
            self.assertIn("BC-07", rules(contract_gate.scan(backend, frontend, contract_file, openapi_file)))

    def test_stale_types_snapshot_is_blocked(self) -> None:
        stack, backend, frontend, contract_file, openapi_file = contract_project()
        with stack:
            types_file = frontend / "src" / "api" / "types.gen.ts"
            types_file.write_text("// openapi-sha256: " + "0" * 64 + "\n", encoding="utf-8")
            self.assertIn("BC-08", rules(contract_gate.scan(backend, frontend, contract_file, openapi_file)))


class TestSecurityGate(unittest.TestCase):
    def test_clean_tree_has_no_blocks(self) -> None:
        stack, backend, frontend = project_with(frontend=True)
        with stack:
            self.assertEqual(blocks(security_gate.scan(backend, frontend)), [])

    def test_extractall_is_blocked(self) -> None:
        code = (
            "import zipfile\n\n\n"
            "def boom(archive: zipfile.ZipFile, target: str) -> None:\n"
            "    archive.extractall(target)\n"
        )
        stack, backend, frontend = project_with({"app/adapters/archive.py": code})
        with stack:
            self.assertIn("BSEC-01", rules(security_gate.scan(backend, frontend)))

    def test_sql_splice_is_blocked(self) -> None:
        code = "def find(conn, plan_id: str):\n    return conn.execute(f'select * from plan where id={plan_id}')\n"
        stack, backend, frontend = project_with({"app/adapters/db/repo.py": code})
        with stack:
            self.assertIn("BSEC-02", rules(security_gate.scan(backend, frontend)))

    def test_missing_trigger_is_blocked(self) -> None:
        trigger = "CREATE TRIGGER plan_version_update BEFORE UPDATE ON plan_version BEGIN SELECT RAISE(ABORT, 'immutable'); END;\n"
        schema = CLEAN_FILES["app/adapters/db/schema.sql"].replace(trigger, "")
        stack, backend, frontend = project_with({"app/adapters/db/schema.sql": schema})
        with stack:
            self.assertIn("BSEC-03", rules(security_gate.scan(backend, frontend)))

    def test_cookie_without_flags_is_blocked(self) -> None:
        code = "def set_session(response, token: str) -> None:\n    response.set_cookie('session', token)\n"
        stack, backend, frontend = project_with({"app/api/deps.py": code})
        with stack:
            self.assertIn("BSEC-04", rules(security_gate.scan(backend, frontend)))

    def test_md5_password_is_blocked(self) -> None:
        code = "import hashlib\n\n\ndef hash_password(p: str) -> str:\n    return hashlib.md5(p.encode()).hexdigest()\n"
        stack, backend, frontend = project_with({"app/domain/security.py": code})
        with stack:
            self.assertIn("BSEC-05", rules(security_gate.scan(backend, frontend)))

    def test_hardcoded_secret_is_blocked(self) -> None:
        config = "MAX_PACKAGE_BYTES = 50 * 1024 * 1024\nSECRET_KEY = 'dev-secret'\n"
        stack, backend, frontend = project_with({"app/config.py": config})
        with stack:
            self.assertIn("BSEC-06", rules(security_gate.scan(backend, frontend)))

    def test_student_pii_is_blocked(self) -> None:
        code = "def label(plan: dict) -> str:\n    return plan.get('studentName', '')\n"
        stack, backend, frontend = project_with({"app/domain/bad.py": code})
        with stack:
            self.assertIn("BSEC-07", rules(security_gate.scan(backend, frontend)))

    def test_plan_logging_is_blocked(self) -> None:
        code = (
            "import logging\n\nlogger = logging.getLogger(__name__)\n\n\n"
            "def run(plan: dict) -> None:\n    logger.info('import %s', plan)\n"
        )
        stack, backend, frontend = project_with({"app/application/bad.py": code})
        with stack:
            self.assertIn("BSEC-08", rules(security_gate.scan(backend, frontend)))

    def test_unused_package_limit_is_blocked(self) -> None:
        files = dict(CLEAN_FILES)
        files["app/application/ingest_service.py"] = "def run() -> None:\n    return None\n"
        stack, backend, frontend = project_with(files)
        with stack:
            self.assertIn("BSEC-09", rules(security_gate.scan(backend, frontend)))

    def test_unsafe_storage_is_blocked(self) -> None:
        code = "from pathlib import Path\n\n\ndef save(root: Path, name: str) -> Path:\n    return root / name\n"
        stack, backend, frontend = project_with({"app/adapters/storage.py": code})
        with stack:
            self.assertIn("BSEC-10", rules(security_gate.scan(backend, frontend)))


class TestGateRunner(unittest.TestCase):
    def test_runner_skips_when_backend_absent(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_backend_gate.py"), "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["skipped"])
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
