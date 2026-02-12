# src/services/category_service.py

"""
Service for managing game categories and collections.

This service handles all category-related operations including creating,
renaming, deleting, and merging categories. It supports both VDF parser
(localconfig.vdf) and Cloud Storage parser.
"""

from __future__ import annotations

from src.core.localconfig_helper import LocalConfigHelper
from src.core.cloud_storage_parser import CloudStorageParser
from src.core.game_manager import GameManager
from src.utils.i18n import t


__all__ = ["CategoryService"]


class CategoryService:
    """
    Service for category management operations.

    Handles category operations for both VDF and Cloud Storage parsers,
    providing a unified interface for category management.
    """

    def __init__(
        self,
        localconfig_helper: LocalConfigHelper | None,
        cloud_parser: CloudStorageParser | None,
        game_manager: GameManager,
    ):
        """
        Initialize the CategoryService.

        Args:
            localconfig_helper: LocalConfig VDF parser (can be None)
            cloud_parser: Cloud Storage parser (can be None)
            game_manager: Game manager instance
        """
        self.localconfig_helper = localconfig_helper
        self.cloud_parser = cloud_parser
        self.game_manager = game_manager

    def get_active_parser(self) -> CloudStorageParser | None:
        """
        Get the currently active parser.

        Returns:
            CloudStorageParser if available, otherwise LocalConfigParser.
        """
        return self.cloud_parser

    def rename_category(self, old_name: str, new_name: str) -> bool:
        """
        Rename a category across all parsers.

        Args:
            old_name: Current category name
            new_name: New category name

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If new name already exists
        """
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
        """
        Delete a category.

        Args:
            category_name: Name of category to delete

        Returns:
            bool: True if successful, False otherwise
        """
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
        """
        Delete multiple categories at once.

        Args:
            categories: List of category names to delete

        Returns:
            bool: True if successful, False otherwise
        """
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

    def check_empty_collection(self, category_name: str, parent_window=None) -> bool:
        """Check if collection is empty and ask user if it should be deleted.

        Args:
            category_name: Name of the collection to check
            parent_window: Parent window for dialog (optional)

        Returns:
            bool: True if collection was deleted, False otherwise
        """
        from PyQt6.QtWidgets import QMessageBox

        games_in_category = self.game_manager.get_games_by_category(category_name)

        if len(games_in_category) == 0:
            # Show dialog
            reply = QMessageBox.question(
                parent_window,
                t("ui.dialog.empty_collection_title"),
                t("ui.dialog.empty_collection_message", name=category_name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.delete_category(category_name)
                return True

        return False

    def merge_categories(self, categories: list[str], target_category: str) -> bool:
        """
        Merge multiple categories into one target category.

        All games from source categories are moved to the target category,
        then source categories are deleted.

        Args:
            categories: List of all categories to merge (including target)
            target_category: The category to merge into

        Returns:
            bool: True if successful, False otherwise
        """
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
        """
        Create a new empty collection.

        Args:
            name: Name of the new collection

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If collection name already exists
        """
        parser = self.get_active_parser()
        if not parser:
            return False

        # Check if collection already exists
        if name in parser.get_all_categories():
            raise ValueError(t("ui.main_window.collection_exists", name=name))

        # Create# Delegate to a dedicated method — add_app_category("") would crash
        # because cloud_storage_parser does int(app_id) internally.
        parser.create_empty_collection(name)

        return True

    def remove_duplicate_collections(self) -> int:
        """
        Remove duplicate collections (Cloud Storage only).

        Identifies collections with identical names, keeping only the first occurrence.

        Returns:
            int: Number of duplicates removed

        Raises:
            RuntimeError: If cloud storage is not available
        """
        if not self.cloud_parser:
            raise RuntimeError(t("ui.main_window.cloud_storage_only"))

        # Remove duplicates using cloud_parser's method
        removed = self.cloud_parser.remove_duplicate_collections()

        return removed

    def get_all_categories(self) -> dict[str, int]:
        """
        Get all categories with game counts.

        Delegates to game_manager for consistent counts.

        Returns:
            dict mapping category names to game counts
        """
        return self.game_manager.get_all_categories()

    def add_app_to_category(self, app_id: str, category: str) -> bool:
        """
        Add an app to a category.

        Args:
            app_id: Steam app ID
            category: Category name

        Returns:
            bool: True if successful, False otherwise
        """
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
        """
        Remove an app from a category.

        Args:
            app_id: Steam app ID
            category: Category name

        Returns:
            bool: True if successful, False otherwise
        """
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
