"""Centralized logging configuration for Steam Library Manager.

Provides a pre-configured logger with console output and optional file logging.
All modules should import the logger from here instead of using print().
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

__all__ = ["logger", "setup_logging"]

logger = logging.getLogger("steamlibmgr")


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
) -> None:
    """Configure the root application logger.

    Args:
        level: The logging level (default: INFO).
        log_file: Optional path to a log file. If provided, logs will
            also be written to this file.
    """
    logger.setLevel(level)

    if logger.handlers:
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
