#
# steam_library_manager/services/smart_collections/smart_collection_manager.py
# Smart Collection lifecycle manager: CRUD, evaluate, sync.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from steam_library_manager.services.smart_collections.evaluator import SmartCollectionEvaluator
from steam_library_manager.services.smart_collections.models import (
    SmartCollection,
    collection_from_json,
    collection_to_json,
)

if TYPE_CHECKING:
    from steam_library_manager.core.database import Database
    from steam_library_manager.core.game import Game
    from steam_library_manager.core.game_manager import GameManager
    from steam_library_manager.services.category_service import CategoryService

__all__ = ["SmartCollectionManager"]

logger = logging.getLogger("steamlibmgr.smart_collections.manager")


class SmartCollectionManager:
    """Manages Smart Collection lifecycle: CRUD, evaluate, sync."""

    def __init__(
        self,
        database: Database,
        game_manager: GameManager,
        category_service: CategoryService | None = None,
    ) -> None:
        self.database = database
        self.game_manager = game_manager
        self.category_service = category_service
        self.evaluator = SmartCollectionEvaluator()

    # CRUD

    def create(self, collection: SmartCollection) -> int:
        """Create a smart collection, evaluate it, and sync to Steam."""
        rules_json = collection_to_json(collection)
        collection_id = self.database.create_smart_collection(
            name=collection.name,
            description=collection.description,
            icon=collection.icon,
            rules_json=rules_json,
        )
        collection.collection_id = collection_id

        # Evaluate and populate
        matching = self.evaluate_collection(collection)
        app_ids = [int(g.app_id) for g in matching]
        self.database.populate_smart_collection(collection_id, app_ids)
        self.database.commit()

        # Sync to Steam
        if collection.auto_sync:
            self.sync_to_steam(collection, [g.app_id for g in matching])

        logger.info(
            "Created smart collection '%s' (id=%d) with %d games",
            collection.name,
            collection_id,
            len(matching),
        )
        return collection_id

    def update(self, collection: SmartCollection) -> int:
        """Update a smart collection, re-evaluate, and re-sync."""
        # Check if name changed - clean up old Steam category
        old_row = self.database.get_smart_collection(collection.collection_id)
        old_name = old_row["name"] if old_row else None

        rules_json = collection_to_json(collection)
        self.database.update_smart_collection(
            collection_id=collection.collection_id,
            name=collection.name,
            description=collection.description,
            icon=collection.icon,
            rules_json=rules_json,
        )

        # If name changed, remove old Steam category
        if old_name and old_name != collection.name:
            self._remove_from_steam(old_name)

        # Re-evaluate and re-populate
        matching = self.evaluate_collection(collection)
        app_ids = [int(g.app_id) for g in matching]
        self.database.populate_smart_collection(collection.collection_id, app_ids)
        self.database.commit()

        # Re-sync to Steam (with new name)
        if collection.auto_sync:
            self.sync_to_steam(collection, [g.app_id for g in matching])

        logger.info(
            "Updated smart collection '%s' (id=%d) with %d games",
            collection.name,
            collection.collection_id,
            len(matching),
        )
        return len(matching)

    def delete(self, collection_id: int) -> None:
        """Delete a smart collection from DB and optionally from Steam."""
        # Get collection info before deleting (for Steam cleanup)
        row = self.database.get_smart_collection(collection_id)
        self.database.delete_smart_collection(collection_id)
        self.database.commit()

        # Remove from Steam cloud if we have a category service
        if row and self.category_service:
            name = row["name"]
            self._remove_from_steam(name)

        logger.info("Deleted smart collection id=%d", collection_id)

    def get_all(self) -> list[SmartCollection]:
        """Load all smart collections from DB."""
        return [self._hydrate_row(row) for row in self.database.get_all_smart_collections()]

    def get_by_name(self, name: str) -> SmartCollection | None:
        """Load a single smart collection by name."""
        row = self.database.get_smart_collection_by_name(name)
        return self._hydrate_row(row) if row else None

    # Evaluation

    def evaluate_collection(self, collection: SmartCollection) -> list[Game]:
        """Evaluate rules against all real games."""
        all_games = self.game_manager.get_real_games()
        return self.evaluator.evaluate_batch(all_games, collection)

    def evaluate_all(self) -> dict[str, list[Game]]:
        """Evaluate all active smart collections."""
        result: dict[str, list[Game]] = {}
        for sc in self.get_all():
            if sc.is_active:
                result[sc.name] = self.evaluate_collection(sc)
        return result

    # Steam sync

    def sync_to_steam(self, collection: SmartCollection, matching_app_ids: list[str]) -> None:
        """Sync a smart collection to Steam, adding/removing games as needed."""
        if not self.category_service:
            return

        matching_set = set(matching_app_ids)

        # Get current games in the Steam category
        current_games = self.game_manager.get_games_by_category(collection.name)
        current_ids = {g.app_id for g in current_games}

        # Add games that now match but aren't in the category
        for app_id in matching_set - current_ids:
            self.category_service.add_app_to_category(app_id, collection.name)

        # Remove games that no longer match
        for app_id in current_ids - matching_set:
            self.category_service.remove_app_from_category(app_id, collection.name)

    def sync_all_to_steam(self) -> None:
        """Re-evaluates and syncs ALL smart collections to Steam."""
        for sc in self.get_all():
            if sc.is_active and sc.auto_sync:
                matching = self.evaluate_collection(sc)
                app_ids = [int(g.app_id) for g in matching]
                self.database.populate_smart_collection(sc.collection_id, app_ids)
                self.sync_to_steam(sc, [g.app_id for g in matching])
        self.database.commit()

    # Auto-update

    def refresh(self) -> dict[str, int]:
        """Re-evaluate all active smart collections and sync."""
        result: dict[str, int] = {}
        for sc in self.get_all():
            if not sc.is_active:
                continue
            matching = self.evaluate_collection(sc)
            app_ids = [int(g.app_id) for g in matching]
            self.database.populate_smart_collection(sc.collection_id, app_ids)

            if sc.auto_sync:
                self.sync_to_steam(sc, [g.app_id for g in matching])

            result[sc.name] = len(matching)

        if result:
            self.database.commit()
            logger.info("Refreshed %d smart collections: %s", len(result), result)
        return result

    # Private helpers

    @staticmethod
    def _hydrate_row(row: dict) -> SmartCollection:
        """Create a SmartCollection from a database row."""
        sc = SmartCollection(
            collection_id=row["collection_id"],
            name=row["name"],
            description=row.get("description", ""),
            icon=row.get("icon", "\U0001f9e0"),
            created_at=row.get("created_at", 0),
        )
        rules_json = row.get("rules", "")
        if rules_json:
            collection_from_json(rules_json, sc)
        return sc

    def _remove_from_steam(self, category_name: str) -> None:
        """Remove all games from a Steam category (for deletion cleanup)."""
        if not self.category_service:
            return
        games = self.game_manager.get_games_by_category(category_name)
        for game in games:
            self.category_service.remove_app_from_category(game.app_id, category_name)
