#
# steam_library_manager/core/db/smart_collection_queries.py
# DB queries for smart collection CRUD and rule persistence
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
    """Mixin for smart collection DB operations.
    Needs ConnectionBase with self.conn.
    """

    def create_smart_collection(self, name, description, icon, rules_json):
        # Insert a new smart collection, return its id
        cursor = self.conn.execute(
            """
            INSERT INTO user_collections (name, description, icon, is_smart, rules, created_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (name, description, icon, rules_json, int(time.time())),
        )
        return cursor.lastrowid or 0

    def update_smart_collection(self, collection_id, name, description, icon, rules_json):
        # Update name, description, icon, rules for a smart collection
        self.conn.execute(
            """
            UPDATE user_collections
            SET name = ?, description = ?, icon = ?, rules = ?
            WHERE collection_id = ? AND is_smart = 1
            """,
            (name, description, icon, rules_json, collection_id),
        )

    def delete_smart_collection(self, collection_id):
        # Remove a smart collection and its game links
        self.conn.execute(
            "DELETE FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        self.conn.execute(
            "DELETE FROM user_collections WHERE collection_id = ? AND is_smart = 1",
            (collection_id,),
        )

    def get_smart_collection(self, collection_id):
        # Fetch one smart collection by id, or None
        cursor = self.conn.execute(
            "SELECT * FROM user_collections WHERE collection_id = ? AND is_smart = 1",
            (collection_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))

    def get_all_smart_collections(self):
        # All smart collections ordered by name
        cursor = self.conn.execute("SELECT * FROM user_collections WHERE is_smart = 1 ORDER BY name")
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get_smart_collection_by_name(self, name):
        # Lookup smart collection by name, or None
        cursor = self.conn.execute(
            "SELECT * FROM user_collections WHERE name = ? AND is_smart = 1",
            (name,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))

    def populate_smart_collection(self, collection_id, app_ids):
        # Replace game membership for a smart collection
        self.conn.execute(
            "DELETE FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        if not app_ids:
            return 0

        now = int(time.time())
        rows = [(collection_id, aid, now) for aid in app_ids]
        self.conn.executemany(
            "INSERT OR IGNORE INTO collection_games (collection_id, app_id, added_at) VALUES (?, ?, ?)",
            rows,
        )
        return len(app_ids)

    def get_smart_collection_games(self, collection_id):
        # All app_ids belonging to a smart collection
        cursor = self.conn.execute(
            "SELECT app_id FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        return [row[0] for row in cursor.fetchall()]
