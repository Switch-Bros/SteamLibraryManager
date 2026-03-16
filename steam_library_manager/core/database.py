#
# steam_library_manager/core/database.py
# Re-export facade for the db/ subpackage
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from steam_library_manager.core.db import Database, DatabaseEntry, ImportStats, database_entry_to_game
from steam_library_manager.core.db.models import is_placeholder_name

__all__ = [
    "Database",
    "DatabaseEntry",
    "ImportStats",
    "database_entry_to_game",
    "is_placeholder_name",
]
