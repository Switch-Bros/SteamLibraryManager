"""Backward-compatible facade for database module.

All code importing from src.core.database continues to work.
The actual implementation lives in src.core.db/ (split into mixins).
"""

from src.core.db import Database, DatabaseEntry, ImportStats, database_entry_to_game
from src.core.db.models import is_placeholder_name

__all__ = [
    "Database",
    "DatabaseEntry",
    "ImportStats",
    "database_entry_to_game",
    "is_placeholder_name",
]
