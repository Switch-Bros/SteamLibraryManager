#
# steam_library_manager/services/category_service.py
# Service for managing game categories and collections
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from steam_library_manager.core.cloud_storage_parser import CloudStorageParser
from steam_library_manager.core.game_manager import GameManager
from steam_library_manager.core.localconfig_helper import LocalConfigHelper
from steam_library_manager.utils.i18n import t

__all__ = ["CategoryService"]


class CategoryService:
    """Service for category management operations."""

    def __init__(
        self,
        localconfig_helper: LocalConfigHelper | None,
        cloud_parser: CloudStorageParser | None,
        game_manager: GameManager,
    ):
        self.localconfig_helper = localconfig_helper
        self.cloud_parser = cloud_parser
        self.game_manager = game_manager

    def get_active_parser(self) -> CloudStorageParser | None:
        """Get the currently active parser."""
        return self.cloud_parser

    def rename_category(self, old_name: str, new_name: str) -> bool:
        """Rename a category across all parsers."""
        parser = self.get_active_parser()
        if not parser:
            return False

        # Check if new name already exists
        if new_name in parser.get_all_categories():
            raise ValueError(t("ui.main_window.collection_exists", name=new_name))

        # Rename in parser
        parser.rename_category(old_name, new_name)

        # Update in-memory games
        for game in self.game_manager.games.values():
            if old_name in game.categories:
                game.categories.remove(old_name)
                game.categories.append(new_name)

        return True

    def delete_category(self, category_name: str) -> bool:
        """Delete a category."""
        parser = self.get_active_parser()
        if not parser:
            return False

        # Delete from parser
        parser.delete_category(category_name)

        # Remove from all games in memory
        for game in self.game_manager.games.values():
            if category_name in game.categories:
                game.categories.remove(category_name)

        return True

    def delete_multiple_categories(self, categories: list[str]) -> bool:
        """Delete multiple categories at once."""
        parser = self.get_active_parser()
        if not parser or not categories:
            return False

        # Delete all categories
        for category in categories:
            parser.delete_category(category)

            # Remove from all games in memory
            for game in self.game_manager.games.values():
                if category in game.categories:
                    game.categories.remove(category)

        return True

    def is_collection_empty(self, category_name: str) -> bool:
        """Check if a collection has no games."""
        return len(self.game_manager.get_games_by_category(category_name)) == 0

    def merge_categories(self, categories: list[str], target_category: str) -> bool:
        """Merge multiple categories into one target category."""
        parser = self.get_active_parser()
        if not parser or len(categories) < 2:
            return False

        # Get source categories (all except target)
        source_categories = [cat for cat in categories if cat != target_category]

        # Merge: Move all games from source to target
        for source_cat in source_categories:
            games_in_source = self.game_manager.get_games_by_category(source_cat)

            for game in games_in_source:
                # Add to target if not already there
                if target_category not in game.categories:
                    game.categories.append(target_category)
                    parser.add_app_category(game.app_id, target_category)

                # Remove from source
                if source_cat in game.categories:
                    game.categories.remove(source_cat)
                    parser.remove_app_category(game.app_id, source_cat)

            # Delete the source category
            parser.delete_category(source_cat)

        return True

    def create_collection(self, name: str) -> bool:
        """Create a new empty collection."""
        parser = self.get_active_parser()
        if not parser:
            return False

        # Check if collection already exists
        if name in parser.get_all_categories():
            raise ValueError(t("ui.main_window.collection_exists", name=name))

        # Delegate to a dedicated method - add_app_category("") would crash
        # because cloud_storage_parser does int(app_id) internally.
        parser.create_empty_collection(name)

        return True

    def remove_duplicate_collections(self) -> int:
        """Remove duplicate collections WITHOUT merging games (Cloud Storage only).

        WARNING: This silently drops games from duplicate collections! For
        user-facing operations, use ``merge_duplicate_collections()`` with
        ``MergeDuplicatesDialog`` instead. This method is retained for
        programmatic/testing use only.

        Identifies collections with identical names, keeping only the first occurrence.
        """
        if not self.cloud_parser:
            raise RuntimeError(t("ui.main_window.cloud_storage_only"))

        removed = self.cloud_parser.remove_duplicate_collections()
        return removed

    def merge_duplicate_collections(self, merge_plan: list[tuple[str, int]]) -> int:
        """Merges duplicate collections based on a user-selected plan."""
        if not self.cloud_parser:
            raise RuntimeError(t("ui.main_window.cloud_storage_only"))

        dup_groups = self.cloud_parser.get_duplicate_groups()
        merged_count = 0

        for name, keep_idx in merge_plan:
            if name not in dup_groups:
                continue

            colls = dup_groups[name]
            if keep_idx < 0 or keep_idx >= len(colls):
                continue

            keep_coll = colls[keep_idx]
            keep_apps = keep_coll.get("added", keep_coll.get("apps", []))
            if not isinstance(keep_apps, list):
                keep_apps = []

            # Merge all app IDs from non-selected collections into the kept one
            merged_app_ids: set[int] = set(keep_apps)
            for idx, coll in enumerate(colls):
                if idx == keep_idx:
                    continue
                apps = coll.get("added", coll.get("apps", []))
                if isinstance(apps, list):
                    merged_app_ids.update(apps)

            # Update the kept collection with merged app IDs
            keep_coll["added"] = sorted(merged_app_ids)

            # Remove the non-selected collections from the parser
            for idx, coll in enumerate(colls):
                if idx != keep_idx and coll in self.cloud_parser.collections:
                    col_id = coll.get("id", "")
                    if col_id:
                        self.cloud_parser._deleted_keys.add(f"user-collections.{col_id}")
                    self.cloud_parser.collections.remove(coll)

            self.cloud_parser.modified = True
            merged_count += 1

        # Re-sync in-memory game.categories from parser state
        if merged_count > 0:
            self._resync_game_categories()

        return merged_count

    def _resync_game_categories(self) -> None:
        """Rebuilds in-memory game.categories from parser collections."""
        if not self.cloud_parser:
            return

        # Build a mapping: app_id (int) -> set of category names
        app_categories: dict[int, list[str]] = {}
        for coll in self.cloud_parser.collections:
            coll_name = coll.get("name", "")
            if not coll_name:
                continue
            apps = coll.get("added", coll.get("apps", []))
            if not isinstance(apps, list):
                continue
            for app_id in apps:
                try:
                    aid = int(app_id)
                except (ValueError, TypeError):
                    continue
                app_categories.setdefault(aid, [])
                if coll_name not in app_categories[aid]:
                    app_categories[aid].append(coll_name)

        # Update each game's categories
        for game in self.game_manager.games.values():
            try:
                aid = int(game.app_id)
            except (ValueError, TypeError):
                continue
            game.categories = app_categories.get(aid, [])

    def get_all_categories(self) -> dict[str, int]:
        """Get all categories with game counts."""
        return self.game_manager.get_all_categories()

    def add_app_to_category(self, app_id: str, category: str) -> bool:
        """Add an app to a category."""
        parser = self.get_active_parser()
        if not parser:
            return False

        parser.add_app_category(app_id, category)

        # Update in-memory game
        if app_id in self.game_manager.games:
            game = self.game_manager.games[app_id]
            if category not in game.categories:
                game.categories.append(category)

        return True

    def remove_app_from_category(self, app_id: str, category: str) -> bool:
        """Remove an app from a category."""
        parser = self.get_active_parser()
        if not parser:
            return False

        parser.remove_app_category(app_id, category)

        # Update in-memory game
        if app_id in self.game_manager.games:
            game = self.game_manager.games[app_id]
            if category in game.categories:
                game.categories.remove(category)

        return True
