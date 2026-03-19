#
# steam_library_manager/ui/actions/game_actions.py
# UI action handlers for per-game context menu operations
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.open_url import open_url

__all__ = ["GameActions"]


class GameActions:
    """Handles per-game context menu actions like favorite, hide,
    store page, and removal. Delegates to parsers/managers via MainWindow.
    """

    def __init__(self, main_window):
        self.mw = main_window

    # ------------------------------------------------------------------
    # Public API - Game Actions
    # ------------------------------------------------------------------

    def toggle_favorite(self, game):
        # Flip favorite status via cloud storage collection
        if not self.mw.cloud_storage_parser:
            return

        fav_key = t("categories.favorites")

        if game.is_favorite():
            if fav_key in game.categories:
                game.categories.remove(fav_key)
            if self.mw.category_service:
                self.mw.category_service.remove_app_from_category(game.app_id, fav_key)
        else:
            if fav_key not in game.categories:
                game.categories.append(fav_key)
            if self.mw.category_service:
                self.mw.category_service.add_app_to_category(game.app_id, fav_key)

        self.mw.save_collections()
        self.mw.populate_categories()

    def toggle_hide_game(self, game, hide):
        # Add/remove from hidden collection
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
            self.mw.set_status("%s: %s" % (status_word, game.name))

            msg = t("ui.visibility.message", game=game.name, status=status_word)
            UIHelper.show_success(self.mw, msg, t("ui.visibility.title"))

    @staticmethod
    def open_in_store(game):
        open_url("https://store.steampowered.com/app/%s" % game.app_id)

    def remove_from_local_config(self, game):
        # Remove ghost entries from localconfig.vdf after confirmation
        if not UIHelper.confirm(
            self.mw, t("ui.dialogs.remove_local_warning", game=game.name), t("ui.dialogs.remove_local_title")
        ):
            return

        if self.mw.localconfig_helper:
            ok = self.mw.localconfig_helper.remove_app(str(game.app_id))
            if ok:
                self.mw.save_collections()

                if self.mw.game_manager and str(game.app_id) in self.mw.game_manager.games:
                    del self.mw.game_manager.games[str(game.app_id)]

                self.mw.populate_categories()

                UIHelper.show_success(
                    self.mw, t("ui.dialogs.remove_local_success", game=game.name), t("common.success")
                )
            else:
                UIHelper.show_error(self.mw, t("ui.dialogs.remove_local_error"))

    def remove_game_from_account(self, game):
        # Opens Steam Support page for permanent game removal
        if UIHelper.confirm(
            self.mw,
            "%s %s" % (t("emoji.warning"), t("ui.dialogs.remove_account_warning")),
            t("ui.dialogs.remove_account_title"),
        ):
            url = "https://help.steampowered.com/en/wizard/HelpWithGameIssue/?appid=%s&issueid=123" % game.app_id
            open_url(url)
