#
# steam_library_manager/ui/actions/game_actions.py
# Context menu actions for individual games
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import TYPE_CHECKING

from steam_library_manager.core.game_manager import Game
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.open_url import open_url

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["GameActions"]


class GameActions:
    """Handles game-specific actions from the context menu."""

    def __init__(self, main_window: "MainWindow") -> None:
        self.mw: "MainWindow" = main_window

    def toggle_favorite(self, game: Game) -> None:
        """Toggles the favorite status of a game."""
        if not self.mw.cloud_storage_parser:
            return

        favorites_key = t("categories.favorites")

        if game.is_favorite():
            if favorites_key in game.categories:
                game.categories.remove(favorites_key)
            if self.mw.category_service:
                self.mw.category_service.remove_app_from_category(game.app_id, favorites_key)
        else:
            if favorites_key not in game.categories:
                game.categories.append(favorites_key)
            if self.mw.category_service:
                self.mw.category_service.add_app_to_category(game.app_id, favorites_key)

        self.mw.save_collections()
        self.mw.populate_categories()

    def toggle_hide_game(self, game: Game, hide: bool) -> None:
        """Toggles the hidden status of a game."""
        if not self.mw.cloud_storage_parser:
            return

        hidden_key = t("categories.hidden")

        if hide:
            if hidden_key not in game.categories:
                game.categories.append(hidden_key)
            if self.mw.category_service:
                self.mw.category_service.add_app_to_category(game.app_id, hidden_key)
        else:
            if hidden_key in game.categories:
                game.categories.remove(hidden_key)
            if self.mw.category_service:
                self.mw.category_service.remove_app_from_category(game.app_id, hidden_key)

        if self.mw.save_collections():
            game.hidden = hide

            self.mw.populate_categories()

            status_word = t("ui.visibility.hidden") if hide else t("ui.visibility.visible")
            self.mw.set_status(f"{status_word}: {game.name}")

            msg = t("ui.visibility.message", game=game.name, status=status_word)
            UIHelper.show_success(self.mw, msg, t("ui.visibility.title"))

    @staticmethod
    def open_in_store(game: Game) -> None:
        """Opens the Steam Store page for a game."""
        open_url(f"https://store.steampowered.com/app/{game.app_id}")

    def remove_from_local_config(self, game: Game) -> None:
        """Removes a ghost game entry from localconfig.vdf after confirmation."""
        if not UIHelper.confirm(
            self.mw, t("ui.dialogs.remove_local_warning", game=game.name), t("ui.dialogs.remove_local_title")
        ):
            return

        if self.mw.localconfig_helper:
            success = self.mw.localconfig_helper.remove_app(str(game.app_id))
            if success:
                self.mw.save_collections()

                if self.mw.game_manager and str(game.app_id) in self.mw.game_manager.games:
                    del self.mw.game_manager.games[str(game.app_id)]

                self.mw.populate_categories()

                UIHelper.show_success(
                    self.mw, t("ui.dialogs.remove_local_success", game=game.name), t("common.success")
                )
            else:
                UIHelper.show_error(self.mw, t("ui.dialogs.remove_local_error"))

    def remove_game_from_account(self, game: Game) -> None:
        """Redirects to Steam Support for permanent game removal."""
        if UIHelper.confirm(
            self.mw,
            f"{t('emoji.warning')} {t('ui.dialogs.remove_account_warning')}",
            t("ui.dialogs.remove_account_title"),
        ):
            url = f"https://help.steampowered.com/en/wizard/HelpWithGameIssue/?appid={game.app_id}&issueid=123"
            open_url(url)
