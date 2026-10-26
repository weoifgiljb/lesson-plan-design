# -*- coding: utf-8 -*-
"""闸门自测共用夹具：在临时目录里搭一棵干净的后端/前端树。"""
from __future__ import annotations

import contextlib
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
ROOT = TEST_DIR.parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@contextlib.contextmanager
def tempdir():
    """沙箱安全的临时目录（见插件测试 support.tempdir 的说明）。"""
    root = Path(tempfile.gettempdir()) / f"lpp-gate-{uuid.uuid4().hex}"
    root.mkdir(mode=0o777)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


CLEAN_FILES = {
    "app/__init__.py": "",
    "app/main.py": (
        "from fastapi import FastAPI\n"
        "\n"
        "\n"
        "def create_app() -> FastAPI:\n"
        "    app = FastAPI()\n"
        "\n"
        "    @app.middleware('http')\n"
        "    async def trace_middleware(request, call_next):\n"
        "        return await call_next(request)\n"
        "\n"
        "    return app\n"
    ),
    "app/config.py": "MAX_PACKAGE_BYTES = 50 * 1024 * 1024\n",
    "app/domain/__init__.py": "",
    "app/domain/errors.py": (
        "ERROR_CODES = {'HASH_MISMATCH': 422}\n"
        "\n"
        "\n"
        "class AppError(Exception):\n"
        "    def __init__(self, code: str, message: str = '') -> None:\n"
        "        self.code = code\n"
        "        super().__init__(message)\n"
    ),
    "app/domain/security.py": (
        "import hashlib\n"
        "\n"
        "\n"
        "def hash_password(password: str, salt: bytes) -> str:\n"
        "    return hashlib.scrypt(password.encode('utf-8'), salt=salt, n=16384, r=8, p=1).hex()\n"
    ),
    "app/domain/versions.py": (
        "VERSIONS = {\n"
        "    'schemaVersion': 1,\n"
        "    'rubricVersion': '1.0',\n"
        "    'rulesVersion': '1.1.0',\n"
        "    'engineVersion': '1.0.0',\n"
        "}\n"
    ),
    "app/domain/ingest.py": (
        "from .errors import AppError\n"
        "\n"
        "\n"
        "def reject(code: str) -> None:\n"
        "    raise AppError(code)\n"
    ),
    "app/application/__init__.py": "",
    "app/application/ingest_service.py": (
        "from app.config import MAX_PACKAGE_BYTES\n"
        "from app.domain.ingest import reject\n"
        "\n"
        "\n"
        "def package_limit() -> int:\n"
        "    return MAX_PACKAGE_BYTES\n"
        "\n"
        "\n"
        "def run() -> None:\n"
        "    reject('HASH_MISMATCH')\n"
    ),
    "app/adapters/__init__.py": "",
    "app/adapters/archive.py": (
        "import zipfile\n"
        "from pathlib import Path\n"
        "\n"
        "\n"
        "def safe_join(root: Path, name: str) -> Path:\n"
        "    target = (root / name).resolve()\n"
        "    if not target.is_relative_to(root.resolve()):\n"
        "        raise ValueError(name)\n"
        "    return target\n"
        "\n"
        "\n"
        "def safe_extract(archive: zipfile.ZipFile, root: Path) -> list[Path]:\n"
        "    return [safe_join(root, item) for item in archive.namelist()]\n"
    ),
    "app/adapters/storage.py": (
        "from pathlib import Path\n"
        "\n"
        "\n"
        "def safe_path(root: Path, relative: str) -> Path:\n"
        "    candidate = (root / relative).resolve()\n"
        "    if not candidate.is_relative_to(root.resolve()):\n"
        "        raise ValueError(relative)\n"
        "    return candidate\n"
    ),
    "app/adapters/engine.py": (
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        "\n"
        "def load(script_dir: Path) -> None:\n"
        "    sys.path.insert(0, str(script_dir))\n"
    ),
    "app/adapters/db/__init__.py": "",
    "app/adapters/db/connection.py": (
        "import sqlite3\n"
        "\n"
        "\n"
        "def connect(path: str) -> sqlite3.Connection:\n"
        "    return sqlite3.connect(path)\n"
    ),
    "app/adapters/db/schema.sql": (
        "PRAGMA journal_mode=WAL;\n"
        "PRAGMA foreign_keys=ON;\n"
        "CREATE TABLE plan_version (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE audit_log (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE sync_log (id INTEGER PRIMARY KEY);\n"
        "CREATE TRIGGER plan_version_update BEFORE UPDATE ON plan_version BEGIN SELECT RAISE(ABORT, 'immutable'); END;\n"
        "CREATE TRIGGER plan_version_delete BEFORE DELETE ON plan_version BEGIN SELECT RAISE(ABORT, 'immutable'); END;\n"
        "CREATE TRIGGER audit_log_update BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'immutable'); END;\n"
        "CREATE TRIGGER audit_log_delete BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'immutable'); END;\n"
        "CREATE TRIGGER sync_log_update BEFORE UPDATE ON sync_log BEGIN SELECT RAISE(ABORT, 'immutable'); END;\n"
        "CREATE TRIGGER sync_log_delete BEFORE DELETE ON sync_log BEGIN SELECT RAISE(ABORT, 'immutable'); END;\n"
    ),
    "app/api/__init__.py": "",
    "app/api/deps.py": (
        "def set_session(response, token: str) -> None:\n"
        "    response.set_cookie('session', token, httponly=True, samesite='Lax')\n"
    ),
    "app/api/errors.py": (
        "def handle(call):\n"
        "    try:\n"
        "        return call()\n"
        "    except Exception:\n"
        "        return None\n"
    ),
    "app/api/routers/__init__.py": "",
    "app/api/routers/plans.py": (
        "from app.application import ingest_service\n"
        "\n"
        "\n"
        "def import_plan() -> None:\n"
        "    ingest_service.run()\n"
    ),
}

CONTRACT = {
    "contractVersion": "1",
    "versions": {
        "schemaVersion": 1,
        "rubricVersion": "1.0",
        "rulesVersion": "1.1.0",
        "engineVersion": "1.0.0",
    },
    "roles": ["teacher", "lead", "admin"],
    "errorCodes": [
        {"code": "HASH_MISMATCH", "http": 422, "zh": "哈希不符"},
    ],
    "endpoints": [
        {
            "method": "GET",
            "path": "/api/v1/plans",
            "auth": True,
            "roles": ["teacher"],
            "csrf": False,
            "idempotent": True,
            "status": [200],
            "client": "ui",
        },
        {
            "method": "POST",
            "path": "/api/v1/plans/import",
            "auth": True,
            "roles": ["teacher"],
            "csrf": True,
            "idempotent": True,
            "status": [201],
            "client": "ui",
        },
    ],
}

FRONTEND_FILES = {
    "src/api/plans.ts": (
        "export async function listPlans() {\n"
        "  return client.get<Plan[]>('/api/v1/plans')\n"
        "}\n"
        "\n"
        "export async function importPlan(body: unknown) {\n"
        "  return client.post('/api/v1/plans/import', body)\n"
        "}\n"
    ),
    "src/api/errors.ts": "export const messages = { HASH_MISMATCH: '哈希不符' }\n",
}


def write_tree(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def make_project(root: Path, *, backend: dict[str, str] | None = None,
                 frontend: dict[str, str] | None = None) -> tuple[Path, Path]:
    backend_root = root / "backend"
    frontend_root = root / "frontend"
    write_tree(backend_root, dict(CLEAN_FILES if backend is None else backend))
    if frontend is not None:
        write_tree(frontend_root, frontend)
    return backend_root, frontend_root


def contract_path(root: Path, contract: dict | None = None) -> Path:
    import json

    path = root / "contract.v1.json"
    path.write_text(json.dumps(contract or CONTRACT, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def openapi_path(root: Path, routes: dict[str, list[str]] | None = None, *, frontend_root: Path | None = None) -> Path:
    import hashlib
    import json

    paths = routes if routes is not None else {
        "/api/v1/plans": ["get"],
        "/api/v1/plans/import": ["post"],
    }
    snapshot = {"openapi": "3.1.0", "paths": {path: {method: {} for method in methods} for path, methods in paths.items()}}
    path = root / "openapi.v1.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    if frontend_root is not None:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        types_file = frontend_root / "src" / "api" / "types.gen.ts"
        types_file.parent.mkdir(parents=True, exist_ok=True)
        types_file.write_text(f"// openapi-sha256: {digest}\nexport type Plan = {{}}\n", encoding="utf-8")
    return path
