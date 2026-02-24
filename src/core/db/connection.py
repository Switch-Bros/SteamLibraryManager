"""Database connection management.

Handles SQLite connection setup, PRAGMA configuration, and
context manager protocol.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["ConnectionBase"]


class ConnectionBase:
    """Base class providing SQLite connection setup and lifecycle.

    Configures WAL mode and foreign keys. Calls _ensure_schema()
    which is provided by SchemaMixin via multiple inheritance.
    """

    SCHEMA_VERSION = 9

    conn: sqlite3.Connection
    db_path: Path

    def __init__(self, db_path: Path) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")

        self._ensure_schema()

    def commit(self) -> None:
        """Commit current transaction."""
        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self) -> ConnectionBase:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.commit()
        self.close()
