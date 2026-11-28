# -*- coding: utf-8 -*-
"""BS-16：文件日志 + 30 天轮转保留。"""
from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_RETENTION_DAYS = 30
LOG_NAME = "app.log"


def configure(log_dir: Path) -> TimedRotatingFileHandler:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / LOG_NAME
    logger = logging.getLogger("lpp")
    logger.setLevel(logging.INFO)
    for handler in list(logger.handlers):
        if isinstance(handler, TimedRotatingFileHandler):
            logger.removeHandler(handler)
            handler.close()
    handler = TimedRotatingFileHandler(
        path,
        when="midnight",
        backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    return handler
