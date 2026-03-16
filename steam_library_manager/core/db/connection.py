#
# steam_library_manager/core/db/connection.py
# SQLite connection setup, PRAGMAs, and context manager
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from steam_library_manager.utils.timeouts import DB_BUSY_TIMEOUT_MS, DB_CONNECT_TIMEOUT

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["ConnectionBase"]


class ConnectionBase:
    """SQLite connection setup and lifecycle (WAL, foreign keys, schema)."""

    SCHEMA_VERSION = 9

    conn: sqlite3.Connection
    db_path: Path

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(db_path), timeout=DB_CONNECT_TIMEOUT)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute(f"PRAGMA busy_timeout = {DB_BUSY_TIMEOUT_MS}")

        self._ensure_schema()

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> ConnectionBase:
        return self

    def __exit__(self, *args: Any) -> None:
        self.commit()
        self.close()
