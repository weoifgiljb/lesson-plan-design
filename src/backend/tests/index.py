# -*- coding: utf-8 -*-
"""后端测试入口：py -3 src/backend/tests/index.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_archive import TestArchive  # noqa: E402,F401
from test_audit_api import TestAuditApi  # noqa: E402,F401
from test_auth_api import TestAuthApi  # noqa: E402,F401
from test_auth_domain import TestAuthRules, TestRoles  # noqa: E402,F401
from test_db_schema import TestDatabaseSchema  # noqa: E402,F401
from test_engine import TestEngineParity  # noqa: E402,F401
from test_errors_api import TestErrorEnvelope  # noqa: E402,F401
from test_export_api import TestExportApi  # noqa: E402,F401
from test_evidence_domain import TestEvidenceChain  # noqa: E402,F401
from test_jwt_auth import TestJwtAuth  # noqa: E402,F401
from test_meta_api import TestMetaApi  # noqa: E402,F401
from test_health import TestHealth, TestOpenApiSnapshot  # noqa: E402,F401
from test_idempotency import TestIdempotency  # noqa: E402,F401
from test_import_api import TestImportApi  # noqa: E402,F401
from test_ingest_domain import TestIngestVerdicts  # noqa: E402,F401
from test_ingest_negative import TestIngestNegative  # noqa: E402,F401
from test_ingest_service import TestIngestService  # noqa: E402,F401
from test_library_domain import TestLibraryRules, TestPlanDiff  # noqa: E402,F401
from test_permissions import TestPermissionMatrix  # noqa: E402,F401
from test_plans_api import TestPlansApi  # noqa: E402,F401
from test_reviews_api import TestReviewsApi  # noqa: E402,F401
from test_repair_schema import TestRepairSchema  # noqa: E402,F401
from test_samples_api import TestSamplesApi  # noqa: E402,F401
from test_security import TestSecurity  # noqa: E402,F401
from test_stats_api import TestStatsApi  # noqa: E402,F401
from test_stats_golden import TestStatsGolden  # noqa: E402,F401
from test_storage import TestStorage  # noqa: E402,F401
from test_sync_api import TestSyncApi  # noqa: E402,F401
from test_tasks_api import TestTasksApi  # noqa: E402,F401
from test_transaction import TestTransactionBoundary  # noqa: E402,F401
from test_users_api import TestUsersApi  # noqa: E402,F401

if __name__ == "__main__":
    import unittest

    unittest.main()
