"""Smart collection database operations.

Handles CRUD for smart (rule-based) collections and their
game memberships.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["SmartCollectionMixin"]


class SmartCollectionMixin:
    """Mixin providing smart collection operations.

    Requires ConnectionBase attributes: conn.
    """

    def create_smart_collection(self, name: str, description: str, icon: str, rules_json: str) -> int:
        """Creates a new smart collection in the database.

        Args:
            name: Collection name (must be unique).
            description: Optional description.
            icon: Emoji icon.
            rules_json: JSON string with logic and rules.

        Returns:
            The new collection_id.
        """
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
        """Updates an existing smart collection.

        Args:
            collection_id: The collection to update.
            name: New name.
            description: New description.
            icon: New icon.
            rules_json: New rules JSON string.
        """
        self.conn.execute(
            """
            UPDATE user_collections
            SET name = ?, description = ?, icon = ?, rules = ?
            WHERE collection_id = ? AND is_smart = 1
            """,
            (name, description, icon, rules_json, collection_id),
        )

    def delete_smart_collection(self, collection_id: int) -> None:
        """Deletes a smart collection and its game associations.

        Args:
            collection_id: The collection to delete.
        """
        self.conn.execute(
            "DELETE FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        self.conn.execute(
            "DELETE FROM user_collections WHERE collection_id = ? AND is_smart = 1",
            (collection_id,),
        )

    def get_smart_collection(self, collection_id: int) -> dict | None:
        """Retrieves a single smart collection by ID.

        Args:
            collection_id: The collection to retrieve.

        Returns:
            Dict with collection fields, or None if not found.
        """
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
        """Retrieves all smart collections ordered by name.

        Returns:
            List of dicts with collection fields.
        """
        cursor = self.conn.execute("SELECT * FROM user_collections WHERE is_smart = 1 ORDER BY name")
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_smart_collection_by_name(self, name: str) -> dict | None:
        """Retrieves a smart collection by name.

        Args:
            name: The collection name.

        Returns:
            Dict with collection fields, or None if not found.
        """
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
        """Replaces the game membership of a smart collection.

        Args:
            collection_id: The collection to populate.
            app_ids: List of app IDs that match the collection rules.

        Returns:
            Number of games added.
        """
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
        """Retrieves all app IDs in a smart collection.

        Args:
            collection_id: The collection to query.

        Returns:
            List of app IDs.
        """
        cursor = self.conn.execute(
            "SELECT app_id FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        return [row[0] for row in cursor.fetchall()]
