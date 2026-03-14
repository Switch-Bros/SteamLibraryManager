#
# steam_library_manager/ui/handlers/category_action_handler.py
# Handler for category (collection) actions and context menus.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMenu, QDialog, QVBoxLayout, QLabel, QListWidget, QDialogButtonBox

from steam_library_manager.core.game_manager import Game
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["CategoryActionHandler"]


class CategoryActionHandler:
    """Handles category/collection CRUD operations and context menus.

    Every mutation method ends with the three-step flush:
    save_collections, populate_categories, update_statistics.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        self.mw: "MainWindow" = main_window

    # Context menus

    def on_game_right_click(self, game: Game, pos) -> None:
        """Show the context menu for a right-clicked game."""
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
        from steam_library_manager.ui.actions.game_actions import GameActions

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
        """Show the context menu for a right-clicked category."""
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
        from steam_library_manager.ui.constants import get_protected_collection_names

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

    # Category CRUD

    def rename_category(self, old_name: str) -> None:
        """Prompt for a new name and rename the category."""
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
        """Confirm and delete a single category."""
        mw = self.mw
        if not mw.category_service:
            return

        if UIHelper.confirm(mw, t("categories.delete_msg", category=category), t("categories.delete_title")):
            mw.category_service.delete_category(category)
            self._flush(stats=True)

    def delete_multiple_categories(self, categories: list[str]) -> None:
        """Confirm and delete multiple categories at once."""
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
        """Show a target-selection dialog and merge categories."""
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
                # All categories have the same name → open merge dialog
                # (not destructive remove - that would lose games!)
                self.show_merge_duplicates_dialog(filter_name=target_category)
                return

            success = mw.category_service.merge_categories(categories, target_category)
            if success:
                self._flush()
                UIHelper.show_success(
                    mw,
                    t("categories.merge_success", target=target_category, count=len(source_categories)),
                    t("categories.merge_title"),
                )

    # Duplicate merging

    def show_merge_duplicates_dialog(self, filter_name: str | None = None) -> None:
        """Show the merge-duplicates dialog and execute the merge."""
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

        from steam_library_manager.ui.dialogs.merge_duplicates_dialog import MergeDuplicatesDialog

        dialog = MergeDuplicatesDialog(mw, dup_groups, filter_name=filter_name)
        if dialog.exec() == MergeDuplicatesDialog.DialogCode.Accepted:
            merge_plan = dialog.get_merge_plan()
            if merge_plan:
                merged = mw.category_service.merge_duplicate_collections(merge_plan)
                if merged > 0:
                    self._flush(stats=True)
                    UIHelper.show_success(mw, t("categories.merge_duplicates_success", count=merged))

    # Collection creation

    def _create_collection_with_games(self, games: list[Game]) -> None:
        """Prompt for a name, create a collection, and add the given games."""
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

    # Internal helpers

    def _flush(self, *, stats: bool = False) -> None:
        """Persist collections and refresh the UI."""
        self.mw.save_collections()
        self.mw.populate_categories()

        if stats:
            self.mw.update_statistics()
