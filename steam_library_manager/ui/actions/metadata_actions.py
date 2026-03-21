#
# steam_library_manager/ui/actions/metadata_actions.py
# UI action handlers for metadata edit and import operations
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: undo support for metadata edits?

from __future__ import annotations

__all__ = ["MetadataActions"]

from typing import TYPE_CHECKING

from steam_library_manager.core.game_manager import Game
from steam_library_manager.ui.dialogs.metadata_dialogs import BulkMetadataEditDialog, MetadataRestoreDialog
from steam_library_manager.ui.dialogs.metadata_edit_dialog import MetadataEditDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow


class MetadataActions:
    """Handles metadata editing, PEGI overrides, and restoration."""

    def __init__(self, main_window: MainWindow) -> None:
        self.mw = main_window

    # metadata editing

    # open metadata editor for single game
    def edit_game_metadata(self, game: Game) -> None:
        if not self.mw.metadata_service:
            return

        # Lazy-load binary VDF on first metadata edit
        if self.mw.appinfo_manager and not self.mw.appinfo_manager.appinfo:
            self.mw.appinfo_manager.load_appinfo()

        meta = self.mw.metadata_service.get_game_metadata(game.app_id, game)
        orig = self.mw.metadata_service.get_original_metadata(game.app_id, meta.copy())

        dialog = MetadataEditDialog(self.mw, game.name, meta, orig)

        if dialog.exec():
            new = dialog.get_metadata()
            if new:
                self.mw.metadata_service.set_game_metadata(game.app_id, new)

                if new.get("name"):
                    game.name = new["name"]

                self.mw.populate_categories()
                self.mw.selection_handler.on_game_selected(game)
                UIHelper.show_success(self.mw, t("ui.metadata_editor.updated_single", game=game.name))

    # bulk edit metadata for selected games
    def bulk_edit_metadata(self) -> None:
        if not self.mw.selected_games or not self.mw.metadata_service:
            UIHelper.show_warning(self.mw, t("ui.errors.no_selection"))
            return

        names = [g.name for g in self.mw.selected_games]
        dialog = BulkMetadataEditDialog(self.mw, self.mw.selected_games, names)

        if dialog.exec():
            settings = dialog.get_metadata()
            if settings:
                # Revert mode: restore all selected games to original metadata
                if settings.get("__revert_to_original__"):
                    count = self.mw.metadata_service.restore_games_to_original(self.mw.selected_games)
                    self.mw.file_actions.refresh_data()
                    UIHelper.show_success(
                        self.mw,
                        t("ui.metadata_editor.bulk_reverted", count=count),
                    )
                    return

                # Normal bulk edit
                name_mods = settings.pop("name_modifications", None)
                count = self.mw.metadata_service.apply_bulk_metadata(self.mw.selected_games, settings, name_mods)
                self.mw.populate_categories()
                UIHelper.show_success(self.mw, t("ui.metadata_editor.updated_bulk", count=count))

    # pegi overrides

    # handle PEGI override from detail view
    def on_pegi_override_requested(self, app_id: str, rating: str) -> None:
        if not self.mw.appinfo_manager:
            return

        # Save override
        if rating:
            self.mw.appinfo_manager.set_app_metadata(app_id, {"pegi_rating": rating})
            self.mw.appinfo_manager.save_appinfo()
            UIHelper.show_success(self.mw, t("ui.pegi_selector.saved", rating=rating))
        else:
            # Remove override
            if app_id in self.mw.appinfo_manager.modifications:
                mod = self.mw.appinfo_manager.modifications[app_id].get("modified", {})
                if "pegi_rating" in mod:
                    del self.mw.appinfo_manager.modifications[app_id]["modified"]["pegi_rating"]
                    self.mw.appinfo_manager.save_appinfo()
                    UIHelper.show_success(self.mw, t("ui.pegi_selector.removed"))

        # Update UI
        if self.mw.game_manager:
            game = self.mw.game_manager.get_game(app_id)
            if game:
                if rating:
                    game.pegi_rating = rating
                else:
                    # Restore original by re-fetching details
                    self.mw.game_manager.fetch_game_details(app_id)

                    # Re-apply other overrides (name, dev, etc.) just in case
                    if self.mw.appinfo_manager:
                        self.mw.game_manager.apply_metadata_overrides(self.mw.appinfo_manager)

                self.mw.selection_handler.on_game_selected(game)

    # metadata restoration

    # restore metadata to original values
    def restore_metadata_changes(self) -> None:
        if not self.mw.metadata_service:
            return

        mods = self.mw.metadata_service.get_modification_count()
        if mods == 0:
            UIHelper.show_success(self.mw, t("ui.metadata_editor.no_changes_to_restore"))
            return

        dialog = MetadataRestoreDialog(self.mw, mods)
        if dialog.exec() and dialog.should_restore():
            try:
                restored = self.mw.metadata_service.restore_modifications()
                if restored > 0:
                    UIHelper.show_success(self.mw, t("ui.metadata_editor.restored_count", count=restored))
                    self.mw.file_actions.refresh_data()
            except Exception as e:
                UIHelper.show_error(self.mw, str(e))
