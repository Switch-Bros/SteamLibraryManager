"""Backward-compatible facade for database module.

All code importing from steam_library_manager.core.database continues to work.
The actual implementation lives in src.core.db/ (split into mixins).
"""

from steam_library_manager.core.db import Database, DatabaseEntry, ImportStats, database_entry_to_game
from steam_library_manager.core.db.models import is_placeholder_name

__all__ = [
    "Database",
    "DatabaseEntry",
    "ImportStats",
    "database_entry_to_game",
    "is_placeholder_name",
]
