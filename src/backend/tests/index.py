# -*- coding: utf-8 -*-
"""后端测试入口：py -3 src/backend/tests/index.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_archive import TestArchive  # noqa: E402,F401
from test_db_schema import TestDatabaseSchema  # noqa: E402,F401
from test_engine import TestEngineParity  # noqa: E402,F401
from test_health import TestHealth, TestOpenApiSnapshot  # noqa: E402,F401
from test_ingest_domain import TestIngestVerdicts  # noqa: E402,F401
from test_ingest_service import TestIngestService  # noqa: E402,F401
from test_security import TestSecurity  # noqa: E402,F401
from test_storage import TestStorage  # noqa: E402,F401

if __name__ == "__main__":
    import unittest

    unittest.main()
