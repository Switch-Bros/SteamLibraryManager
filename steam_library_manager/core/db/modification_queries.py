#
# steam_library_manager/core/db/modification_queries.py
# Track, query, sync, and revert user metadata modifications
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
import time
from typing import Any

from steam_library_manager.core.db.models import DatabaseEntry

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["ModificationMixin"]


class ModificationMixin:
    """Modification tracking. Requires ``conn`` and ``update_game()``."""

    def track_modification(self, app_id: int, original_data: dict[str, Any], modified_data: dict[str, Any]) -> None:
        """Store original and modified metadata for an app."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO metadata_modifications
            (app_id, original_data, modified_data, modification_time, synced_to_appinfo)
            VALUES (?, ?, ?, ?, 0)
            """,
            (app_id, json.dumps(original_data), json.dumps(modified_data), int(time.time())),
        )
        self.conn.commit()

    def get_modified_games(self, synced_only: bool = False) -> dict[int, dict[str, Any]]:
        """All modifications, optionally filtered to unsynced only."""
        query = "SELECT * FROM metadata_modifications"
        if synced_only:
            query += " WHERE synced_to_appinfo = 0"

        cursor = self.conn.execute(query)

        modifications: dict[int, dict[str, Any]] = {}
        for row in cursor.fetchall():
            modifications[row["app_id"]] = {
                "original": json.loads(row["original_data"]),
                "modified": json.loads(row["modified_data"]),
                "modification_time": row["modification_time"],
                "synced": bool(row["synced_to_appinfo"]),
                "sync_time": row["sync_time"],
            }

        return modifications

    def mark_synced(self, app_id: int) -> None:
        """Mark a game as synced to appinfo.vdf."""
        self.conn.execute(
            """
            UPDATE metadata_modifications
            SET synced_to_appinfo = 1, sync_time = ?
            WHERE app_id = ?
            """,
            (int(time.time()), app_id),
        )
        self.conn.execute("UPDATE games SET last_synced = ? WHERE app_id = ?", (int(time.time()), app_id))
        self.conn.commit()

    def revert_modification(self, app_id: int) -> DatabaseEntry | None:
        """Revert a game to its original metadata. Returns the restored entry."""
        cursor = self.conn.execute("SELECT original_data FROM metadata_modifications WHERE app_id = ?", (app_id,))
        row = cursor.fetchone()

        if not row:
            return None

        original_data = json.loads(row[0])

        entry = DatabaseEntry(app_id=app_id, **original_data)
        self.update_game(entry)

        self.conn.execute("DELETE FROM metadata_modifications WHERE app_id = ?", (app_id,))
        self.conn.commit()

        return entry
