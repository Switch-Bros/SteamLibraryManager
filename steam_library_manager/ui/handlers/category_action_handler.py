#
# steam_library_manager/ui/handlers/category_action_handler.py
# Handler for category (collection) actions and context menus.
#
# Copyright (c) 2025-2026 SwitchBros
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
    """Handles category/collection CRUD and context menus.

    Every mutation ends with _flush() to persist + refresh UI.
    """

    def __init__(self, main_window: "MainWindow"):
        # keep ref to main window for accessing services
        self.mw = main_window

    def on_game_right_click(self, game: Game, pos):
        # build context menu for game item
        mw = self.mw
        menu = QMenu(mw)

        menu.addAction(t("ui.context_menu.view_details"), lambda: mw.selection_handler.on_game_selected(game))
        menu.addAction(t("ui.context_menu.toggle_favorite"), lambda: mw.game_actions.toggle_favorite(game))

        menu.addSeparator()

        # hide/unhide toggle
        if hasattr(game, "hidden"):
            if game.hidden:
                menu.addAction(t("ui.context_menu.unhide_game"), lambda: mw.game_actions.toggle_hide_game(game, False))
            else:
                menu.addAction(t("ui.context_menu.hide_game"), lambda: mw.game_actions.toggle_hide_game(game, True))

        menu.addAction(t("ui.context_menu.remove_from_local"), lambda: mw.game_actions.remove_from_local_config(game))
        menu.addAction(t("ui.context_menu.remove_from_account"), lambda: mw.game_actions.remove_game_from_account(game))

        menu.addSeparator()

        from steam_library_manager.ui.actions.game_actions import GameActions

        menu.addAction(t("ui.context_menu.open_store"), lambda: GameActions.open_in_store(game))
        menu.addAction(
            "%s %s" % (t("emoji.search"), t("ui.context_menu.check_store")),
            lambda: mw.tools_actions.check_store_availability(game),
        )

        menu.addSeparator()

        # auto-categorize: single or multi-selection
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

    def on_category_right_click(self, category, pos):
        # context menu for category tree item
        mw = self.mw
        menu = QMenu(mw)

        # multi-selection handling
        if category == "__MULTI__":
            sel_cats = mw.tree.get_selected_categories()
            if len(sel_cats) > 1:
                menu.addAction(t("ui.context_menu.merge_categories"), lambda: self.merge_categories(sel_cats))
                menu.addSeparator()
                menu.addAction(t("common.delete"), lambda: self.delete_multiple_categories(sel_cats))
            menu.exec(pos)
            return

        # steam collections are protected - read-only
        from steam_library_manager.ui.constants import get_protected_collection_names

        if category in get_protected_collection_names():
            # only auto-categorize allowed, nothing else
            menu.addAction(t("menu.edit.auto_categorize"), lambda: mw.edit_actions.auto_categorize_category(category))
            menu.exec(pos)
            return

        # normal user category
        menu.addAction(t("common.rename"), lambda: self.rename_category(category))
        menu.addAction(t("common.delete"), lambda: self.delete_category(category))

        # check for duplicates in this cat
        if mw.cloud_storage_parser:
            dups = mw.cloud_storage_parser.get_duplicate_groups()
            if category in dups:
                menu.addSeparator()
                menu.addAction(
                    t("ui.context_menu.merge_duplicate_collection", name=category),
                    lambda: self.show_merge_duplicates_dialog(filter_name=category),
                )

        menu.addSeparator()
        menu.addAction(t("menu.edit.auto_categorize"), lambda: mw.edit_actions.auto_categorize_category(category))

        menu.exec(pos)

    def rename_category(self, old_name):
        # prompt for new name
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

    def delete_category(self, cat):
        # confirm then nuke it
        mw = self.mw
        if not mw.category_service:
            return

        if UIHelper.confirm(mw, t("categories.delete_msg", category=cat), t("categories.delete_title")):
            mw.category_service.delete_category(cat)
            self._flush(stats=True)

    def delete_multiple_categories(self, cats):
        # bulk delete with bullet list
        mw = self.mw
        if not mw.category_service or not cats:
            return

        # build bullet list for dialog
        bullets = "\n• ".join(cats)
        msg = t("categories.delete_multiple_msg", count=len(cats), category_list="• %s" % bullets)

        if UIHelper.confirm(mw, msg, t("categories.delete_title")):
            mw.category_service.delete_multiple_categories(cats)
            self._flush(stats=True)

    def merge_categories(self, cats):
        # show target picker and merge
        mw = self.mw
        if not mw.category_service or len(cats) < 2:
            return

        # build dialog inline - ugh, should be separate class
        dlg = QDialog(mw)
        dlg.setWindowTitle(t("categories.merge_title"))
        dlg.setMinimumWidth(400)

        layout = QVBoxLayout()

        lbl = QLabel(t("categories.merge_instruction", count=len(cats)))
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        lst = QListWidget()
        for c in sorted(cats):
            lst.addItem(c)
        lst.setCurrentRow(0)
        layout.addWidget(lst)

        # buttons
        btns = QDialogButtonBox()
        btns.addButton(t("common.ok"), QDialogButtonBox.ButtonRole.AcceptRole)
        btns.addButton(t("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        dlg.setLayout(layout)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            item = lst.currentItem()
            if not item:
                return

            target = item.text()
            src = [c for c in cats if c != target]

            if not src:
                # all same name -> merge dups
                self.show_merge_duplicates_dialog(filter_name=target)
                return

            if mw.category_service.merge_categories(cats, target):
                self._flush()
                UIHelper.show_success(
                    mw,
                    t("categories.merge_success", target=target, count=len(src)),
                    t("categories.merge_title"),
                )

    def show_merge_duplicates_dialog(self, filter_name=None):
        # handle duplicate collection names
        mw = self.mw
        if not mw.cloud_storage_parser or not mw.category_service:
            UIHelper.show_error(mw, t("ui.main_window.cloud_storage_only"))
            return

        groups = mw.cloud_storage_parser.get_duplicate_groups()
        if not groups:
            UIHelper.show_info(mw, t("categories.no_duplicates_found"))
            return

        if filter_name and filter_name not in groups:
            UIHelper.show_info(mw, t("categories.no_duplicates_found"))
            return

        from steam_library_manager.ui.dialogs.merge_duplicates_dialog import MergeDuplicatesDialog

        dlg = MergeDuplicatesDialog(mw, groups, filter_name=filter_name)
        if dlg.exec() == MergeDuplicatesDialog.DialogCode.Accepted:
            plan = dlg.get_merge_plan()
            if plan:
                merged = mw.category_service.merge_duplicate_collections(plan)
                if merged > 0:
                    self._flush(stats=True)
                    UIHelper.show_success(mw, t("categories.merge_duplicates_success", count=merged))

    def _create_collection_with_games(self, games: list[Game]):
        # prompt name, create, add games
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

        for g in games:
            mw.category_service.add_app_to_category(g.app_id, name)

        self._flush()

        if games:
            UIHelper.show_success(
                mw,
                t("ui.main_window.collection_created_with_games", name=name, count=len(games)),
            )
        else:
            UIHelper.show_success(mw, t("ui.main_window.collection_created", name=name))

    def _flush(self, stats=False):
        # persist and refresh
        self.mw.save_collections()
        self.mw.populate_categories()
        if stats:
            self.mw.update_statistics()
