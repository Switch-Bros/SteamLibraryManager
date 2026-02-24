# src/ui/handlers/category_action_handler.py

"""
Handler for all category (collection) actions and context menus.

Extracts the following methods from MainWindow:
  - on_game_right_click / on_category_right_click   (context menus)
  - remove_duplicate_collections                    (bulk cleanup)
  - rename_category                                  (CRUD)
  - delete_category / delete_multiple_categories    (CRUD)
  - merge_categories                                (CRUD)

All persistence (save / populate / update stats) is delegated back to
MainWindow via the stored reference so that the rest of the window's
state stays in sync.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMenu, QDialog, QVBoxLayout, QLabel, QListWidget, QDialogButtonBox

from src.core.game_manager import Game
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

__all__ = ["CategoryActionHandler"]


class CategoryActionHandler:
    """Handles all category/collection CRUD operations and context menus.

    Holds a single back-reference to MainWindow.  Every method that mutates
    data ends with the standard three-step flush:
        1. ``mw.save_collections()``   – persist to VDF / cloud
        2. ``mw.populate_categories()`` – rebuild the tree widget
        3. ``mw.update_statistics()``   – refresh the status-bar counters

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initializes the handler.

        Args:
            main_window: The MainWindow instance that owns this handler.
        """
        self.mw: "MainWindow" = main_window

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------

    def on_game_right_click(self, game: Game, pos) -> None:
        """Shows the context menu for a right-clicked game.

        Args:
            game: The game that was right-clicked.
            pos:  The global screen position for the popup.
        """
        mw = self.mw
        menu = QMenu(mw)

        menu.addAction(t("ui.context_menu.view_details"), lambda: mw.selection_handler.on_game_selected(game))
        menu.addAction(t("ui.context_menu.toggle_favorite"), lambda: mw.game_actions.toggle_favorite(game))

        menu.addSeparator()

        # Hide / Unhide toggle
        if hasattr(game, "hidden"):
            if game.hidden:
                menu.addAction(t("ui.context_menu.unhide_game"), lambda: mw.game_actions.toggle_hide_game(game, False))
            else:
                menu.addAction(t("ui.context_menu.hide_game"), lambda: mw.game_actions.toggle_hide_game(game, True))

        menu.addAction(t("ui.context_menu.remove_from_local"), lambda: mw.game_actions.remove_from_local_config(game))
        menu.addAction(t("ui.context_menu.remove_from_account"), lambda: mw.game_actions.remove_game_from_account(game))

        menu.addSeparator()
        # Note: open_in_store is now a static method in GameActions
        from src.ui.actions.game_actions import GameActions

        menu.addAction(t("ui.context_menu.open_store"), lambda: GameActions.open_in_store(game))
        menu.addAction(
            f"{t('emoji.search')} {t('ui.context_menu.check_store')}",
            lambda: mw.tools_actions.check_store_availability(game),
        )

        menu.addSeparator()

        # Auto-categorize: single game or current multi-selection
        if len(mw.selected_games) > 1:
            menu.addAction(t("menu.edit.auto_categorize"), mw.edit_actions.auto_categorize_selected)
        else:
            menu.addAction(t("menu.edit.auto_categorize"), lambda: mw.edit_actions.auto_categorize_single(game))

        menu.addSeparator()
        menu.addAction(t("ui.context_menu.edit_metadata"), lambda: mw.metadata_actions.edit_game_metadata(game))

        menu.addSeparator()
        menu.addAction(
            t("ui.context_menu.create_collection"),
            lambda: self._create_collection_with_games(mw.selected_games or [game]),
        )
        menu.addAction(
            t("ui.context_menu.create_smart_collection"),
            mw.edit_actions.create_smart_collection,
        )

        menu.exec(pos)

    def on_category_right_click(self, category: str, pos) -> None:
        """Shows the context menu for a right-clicked category.

        Handles three cases:
            1. Multi-category selection  → merge + delete
            2. Special categories        → create + auto-categorize only
            3. Normal categories         → full CRUD menu

        Args:
            category: The category name, or ``"__MULTI__"`` for multi-select.
            pos:      The global screen position for the popup.
        """
        mw = self.mw
        menu = QMenu(mw)

        # --- Multi-category selection ---
        if category == "__MULTI__":
            selected_categories: list[str] = mw.tree.get_selected_categories()
            if len(selected_categories) > 1:
                menu.addAction(
                    t("ui.context_menu.merge_categories"), lambda: self.merge_categories(selected_categories)
                )
                menu.addSeparator()
                menu.addAction(t("common.delete"), lambda: self.delete_multiple_categories(selected_categories))
            menu.exec(pos)
            return

        # --- Steam-Standard-Collections are not editable ---
        from src.ui.constants import get_protected_collection_names

        if category in get_protected_collection_names():
            # ONLY allow Auto-Categorize, NOTHING else!
            menu.addAction(t("menu.edit.auto_categorize"), lambda: mw.edit_actions.auto_categorize_category(category))
            menu.exec(pos)
            return

        else:
            # --- Normal user category ---
            menu.addAction(t("common.rename"), lambda: self.rename_category(category))
            menu.addAction(t("common.delete"), lambda: self.delete_category(category))

            # Check if this category has duplicates
            if mw.cloud_storage_parser:
                dup_groups = mw.cloud_storage_parser.get_duplicate_groups()
                if category in dup_groups:
                    menu.addSeparator()
                    menu.addAction(
                        t("ui.context_menu.merge_duplicate_collection", name=category),
                        lambda: self.show_merge_duplicates_dialog(filter_name=category),
                    )

            menu.addSeparator()
            menu.addAction(t("menu.edit.auto_categorize"), lambda: mw.edit_actions.auto_categorize_category(category))

        menu.exec(pos)

    # ------------------------------------------------------------------
    # Category CRUD
    # ------------------------------------------------------------------

    def remove_duplicate_collections(self) -> None:
        """Removes duplicate collections via CategoryService.

        Confirms with the user first.  Shows a success count or an info
        message when no duplicates were found.
        """
        mw = self.mw
        if not mw.category_service:
            return

        if not UIHelper.confirm(
            mw, t("ui.main_window.remove_duplicates_confirm"), t("ui.main_window.remove_duplicates_title")
        ):
            return

        try:
            removed: int = mw.category_service.remove_duplicate_collections()

            if removed > 0:
                self._flush()
                UIHelper.show_success(mw, t("ui.main_window.duplicates_removed", count=removed))
            else:
                UIHelper.show_info(mw, t("ui.main_window.no_duplicates"))
        except RuntimeError as e:
            UIHelper.show_error(mw, str(e))

    def rename_category(self, old_name: str) -> None:
        """Prompts the user for a new name and renames the category.

        Args:
            old_name: The current name of the category.
        """
        mw = self.mw
        if not mw.category_service:
            return

        new_name, ok = UIHelper.ask_text(mw, t("categories.rename_title"), t("categories.rename_msg", old=old_name))

        if ok and new_name and new_name != old_name:
            try:
                mw.category_service.rename_category(old_name, new_name)
                self._flush(stats=True)
            except ValueError as e:
                UIHelper.show_error(mw, str(e))

    def delete_category(self, category: str) -> None:
        """Confirms and deletes a single category.

        Args:
            category: The name of the category to delete.
        """
        mw = self.mw
        if not mw.category_service:
            return

        if UIHelper.confirm(mw, t("categories.delete_msg", category=category), t("categories.delete_title")):
            mw.category_service.delete_category(category)
            self._flush(stats=True)

    def delete_multiple_categories(self, categories: list[str]) -> None:
        """Confirms and deletes multiple categories at once.

        Args:
            categories: List of category names to delete.
        """
        mw = self.mw
        if not mw.category_service or not categories:
            return

        # Build bullet-point list for the confirmation dialog
        category_list: str = "\n• ".join(categories)
        message: str = t("categories.delete_multiple_msg", count=len(categories), category_list=f"• {category_list}")

        if UIHelper.confirm(mw, message, t("categories.delete_title")):
            mw.category_service.delete_multiple_categories(categories)
            self._flush(stats=True)

    def merge_categories(self, categories: list[str]) -> None:
        """Shows a target-selection dialog and merges categories.

        All games from the non-target categories are moved into the chosen
        target, then the source categories are deleted.

        Args:
            categories: List of category names to merge (must be ≥ 2).
        """
        mw = self.mw
        if not mw.category_service or len(categories) < 2:
            return

        # --- Build the selection dialog inline (small, one-off UI) ---
        dialog = QDialog(mw)
        dialog.setWindowTitle(t("categories.merge_title"))
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Instruction text
        label = QLabel(t("categories.merge_instruction", count=len(categories)))
        label.setWordWrap(True)
        layout.addWidget(label)

        # Sorted list of categories
        list_widget = QListWidget()
        for cat in sorted(categories):
            list_widget.addItem(cat)
        list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)

        # OK / Cancel
        button_box = QDialogButtonBox()
        button_box.addButton(t("common.ok"), QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(t("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        # --- Execute and process result ---
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_item = list_widget.currentItem()
            if not selected_item:
                return

            target_category: str = selected_item.text()
            source_categories: list[str] = [cat for cat in categories if cat != target_category]

            if not source_categories:
                # All categories have the same name → deduplicate instead of merge
                removed = mw.category_service.remove_duplicate_collections()
                self._flush()
                if removed > 0:
                    UIHelper.show_success(
                        mw,
                        t("categories.duplicates_removed", count=removed),
                        t("categories.merge_title"),
                    )
                return

            success = mw.category_service.merge_categories(categories, target_category)
            if success:
                self._flush()
                UIHelper.show_success(
                    mw,
                    t("categories.merge_success", target=target_category, count=len(source_categories)),
                    t("categories.merge_title"),
                )

    # ------------------------------------------------------------------
    # Duplicate merging
    # ------------------------------------------------------------------

    def show_merge_duplicates_dialog(self, filter_name: str | None = None) -> None:
        """Shows the merge-duplicates dialog and executes the merge.

        Detects duplicate collection groups from the cloud parser, opens
        the selection dialog, and merges based on the user's choices.

        Args:
            filter_name: If set, only show the group with this name
                (used from the context menu).
        """
        mw = self.mw
        if not mw.cloud_storage_parser or not mw.category_service:
            UIHelper.show_error(mw, t("ui.main_window.cloud_storage_only"))
            return

        dup_groups = mw.cloud_storage_parser.get_duplicate_groups()
        if not dup_groups:
            UIHelper.show_info(mw, t("categories.no_duplicates_found"))
            return

        # If filtering by name and that name has no duplicates
        if filter_name and filter_name not in dup_groups:
            UIHelper.show_info(mw, t("categories.no_duplicates_found"))
            return

        from src.ui.dialogs.merge_duplicates_dialog import MergeDuplicatesDialog

        dialog = MergeDuplicatesDialog(mw, dup_groups, filter_name=filter_name)
        if dialog.exec() == MergeDuplicatesDialog.DialogCode.Accepted:
            merge_plan = dialog.get_merge_plan()
            if merge_plan:
                merged = mw.category_service.merge_duplicate_collections(merge_plan)
                if merged > 0:
                    self._flush(stats=True)
                    UIHelper.show_success(mw, t("categories.merge_duplicates_success", count=merged))

    # ------------------------------------------------------------------
    # Collection creation with games
    # ------------------------------------------------------------------

    def _create_collection_with_games(self, games: list[Game]) -> None:
        """Prompts for a name, creates a collection, and adds the given games.

        Args:
            games: The games to add to the newly created collection.
        """
        mw = self.mw
        if not mw.category_service:
            return

        name, ok = UIHelper.ask_text(
            mw,
            t("ui.main_window.create_collection_title"),
            t("ui.main_window.create_collection_prompt"),
        )
        if not ok or not name:
            return

        try:
            mw.category_service.create_collection(name)
        except ValueError as e:
            UIHelper.show_error(mw, str(e))
            return

        for game in games:
            mw.category_service.add_app_to_category(game.app_id, name)

        self._flush()

        if games:
            UIHelper.show_success(
                mw,
                t("ui.main_window.collection_created_with_games", name=name, count=len(games)),
            )
        else:
            UIHelper.show_success(
                mw,
                t("ui.main_window.collection_created", name=name),
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flush(self, *, stats: bool = False) -> None:
        """Persists collections and refreshes the UI.

        Every mutation method ends with this single call instead of
        manually chaining save / populate / update_statistics.

        Args:
            stats: If True, also refresh the statistics label.
        """
        self.mw.save_collections()
        self.mw.populate_categories()

        if stats:
            self.mw.update_statistics()
