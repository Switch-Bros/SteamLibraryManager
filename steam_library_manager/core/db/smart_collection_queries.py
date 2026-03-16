#
# steam_library_manager/core/db/smart_collection_queries.py
# CRUD for smart (rule-based) collections and game memberships
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["SmartCollectionMixin"]


class SmartCollectionMixin:
    """Smart collection operations. Requires ``conn``."""

    def create_smart_collection(self, name: str, description: str, icon: str, rules_json: str) -> int:
        """Insert a new smart collection. Returns the new collection_id."""
        cursor = self.conn.execute(
            """
            INSERT INTO user_collections (name, description, icon, is_smart, rules, created_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (name, description, icon, rules_json, int(time.time())),
        )
        return cursor.lastrowid or 0

    def update_smart_collection(
        self, collection_id: int, name: str, description: str, icon: str, rules_json: str
    ) -> None:
        self.conn.execute(
            """
            UPDATE user_collections
            SET name = ?, description = ?, icon = ?, rules = ?
            WHERE collection_id = ? AND is_smart = 1
            """,
            (name, description, icon, rules_json, collection_id),
        )

    def delete_smart_collection(self, collection_id: int) -> None:
        """Delete collection and its game associations."""
        self.conn.execute(
            "DELETE FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        self.conn.execute(
            "DELETE FROM user_collections WHERE collection_id = ? AND is_smart = 1",
            (collection_id,),
        )

    def get_smart_collection(self, collection_id: int) -> dict | None:
        cursor = self.conn.execute(
            "SELECT * FROM user_collections WHERE collection_id = ? AND is_smart = 1",
            (collection_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    def get_all_smart_collections(self) -> list[dict]:
        """All smart collections, ordered by name."""
        cursor = self.conn.execute("SELECT * FROM user_collections WHERE is_smart = 1 ORDER BY name")
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_smart_collection_by_name(self, name: str) -> dict | None:
        cursor = self.conn.execute(
            "SELECT * FROM user_collections WHERE name = ? AND is_smart = 1",
            (name,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    def populate_smart_collection(self, collection_id: int, app_ids: list[int]) -> int:
        """Replace collection membership with the given app_ids."""
        self.conn.execute(
            "DELETE FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        if not app_ids:
            return 0

        now = int(time.time())
        rows = [(collection_id, app_id, now) for app_id in app_ids]
        self.conn.executemany(
            "INSERT OR IGNORE INTO collection_games (collection_id, app_id, added_at) VALUES (?, ?, ?)",
            rows,
        )
        return len(app_ids)

    def get_smart_collection_games(self, collection_id: int) -> list[int]:
        """All app IDs belonging to this collection."""
        cursor = self.conn.execute(
            "SELECT app_id FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        return [row[0] for row in cursor.fetchall()]
