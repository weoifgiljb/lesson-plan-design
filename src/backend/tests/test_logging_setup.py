# -*- coding: utf-8 -*-
"""BS-16：文件日志按天轮转并保留 30 天。"""
from __future__ import annotations

import logging
import unittest

from support import tempdir

from app.logging_setup import LOG_RETENTION_DAYS, configure


class TestLoggingSetup(unittest.TestCase):
    def test_timed_handler_keeps_thirty_days(self) -> None:
        with tempdir() as root:
            handler = configure(root / "logs")
            try:
                self.assertEqual(handler.backupCount, 30)
                self.assertEqual(LOG_RETENTION_DAYS, 30)
                logging.getLogger("lpp").info("test log line")
                handler.flush()
                self.assertTrue((root / "logs" / "app.log").is_file())
            finally:
                logging.getLogger("lpp").removeHandler(handler)
                handler.close()


if __name__ == "__main__":
    unittest.main()
