# src/ui/handlers/empty_collection_handler.py

"""
Handler for automatic deletion of empty collections.

Uses CategoryService to check and delete empty collections automatically
after removing games.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Set, Optional

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class EmptyCollectionHandler:
    """Handles automatic deletion of empty user collections."""

    def __init__(self, main_window: 'MainWindow') -> None:
        """Initialize the handler.

        Args:
            main_window: The MainWindow instance.
        """
        self.mw: 'MainWindow' = main_window
        self._protected_collections: Optional[Set[str]] = None

    def get_protected_collections(self) -> Set[str]:
        """Get the set of Steam standard collections that cannot be deleted.

        Returns:
            Set of protected collection names (translated).
        """
        if self._protected_collections is None:
            from src.utils.i18n import t
            self._protected_collections = {
                t('ui.categories.all_games'),
                t('ui.categories.favorites'),
                t('ui.categories.uncategorized'),
                t('ui.categories.hidden')
            }
        return self._protected_collections

    def check_and_delete_if_empty(self, category_name: str) -> bool:
        """Check if collection is empty and delete it automatically (no dialog).

        This is the original behavior before the "don't delete empty" change.

        Args:
            category_name: Name of the collection to check.

        Returns:
            True if collection was deleted, False otherwise.
        """
        # Never delete Steam standard collections
        if category_name in self.get_protected_collections():
            return False

        if not self.mw.game_manager or not self.mw.category_service:
            return False

        # Check if collection is empty
        games_in_category = self.mw.game_manager.get_games_by_category(category_name)

        if len(games_in_category) == 0:
            # Collection is empty - delete it automatically (original behavior)
            self.mw.category_service.delete_category(category_name)
            return True

        return False