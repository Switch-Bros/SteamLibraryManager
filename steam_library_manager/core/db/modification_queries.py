#
# steam_library_manager/core/db/modification_queries.py
# DB queries for modifying game records and category assignments
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import json
import logging
import time

from steam_library_manager.core.db.models import DatabaseEntry

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["ModificationMixin"]


class ModificationMixin:
    """Mixin for modification tracking on game metadata.
    Needs ConnectionBase (conn) and GameQueryMixin (update_game).
    """

    def track_modification(self, app_id, original_data, modified_data):
        # Store original vs modified snapshot for later sync/revert
        self.conn.execute(
            """
            INSERT OR REPLACE INTO metadata_modifications
            (app_id, original_data, modified_data, modification_time, synced_to_appinfo)
            VALUES (?, ?, ?, ?, 0)
            """,
            (app_id, json.dumps(original_data), json.dumps(modified_data), int(time.time())),
        )
        self.conn.commit()

    def get_modified_games(self, synced_only=False):
        # Returns {app_id: modification_dict} for all tracked changes
        query = "SELECT * FROM metadata_modifications"
        if synced_only:
            query += " WHERE synced_to_appinfo = 0"

        cursor = self.conn.execute(query)

        mods = {}
        for row in cursor.fetchall():
            mods[row["app_id"]] = {
                "original": json.loads(row["original_data"]),
                "modified": json.loads(row["modified_data"]),
                "modification_time": row["modification_time"],
                "synced": bool(row["synced_to_appinfo"]),
                "sync_time": row["sync_time"],
            }

        return mods

    def mark_synced(self, app_id):
        # Flag a game as written back to appinfo.vdf
        now = int(time.time())
        self.conn.execute(
            """
            UPDATE metadata_modifications
            SET synced_to_appinfo = 1, sync_time = ?
            WHERE app_id = ?
            """,
            (now, app_id),
        )
        self.conn.execute("UPDATE games SET last_synced = ? WHERE app_id = ?", (now, app_id))
        self.conn.commit()

    def revert_modification(self, app_id):
        # Restore original data and delete the modification record
        cursor = self.conn.execute("SELECT original_data FROM metadata_modifications WHERE app_id = ?", (app_id,))
        row = cursor.fetchone()

        if not row:
            return None

        orig = json.loads(row[0])

        entry = DatabaseEntry(app_id=app_id, **orig)
        self.update_game(entry)

        self.conn.execute("DELETE FROM metadata_modifications WHERE app_id = ?", (app_id,))
        self.conn.commit()

        return entry
