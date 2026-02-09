# src/ui/actions/game_actions.py

"""
Action handler for game-specific operations (context menu).

Extracts the following methods from MainWindow:
  - toggle_favorite(game)             (add/remove from favorites)
  - toggle_hide_game(game, hide)      (show/hide game in library)
  - open_in_store(game)               (open Steam Store page)
  - remove_from_local_config(game)    (remove from localconfig.vdf)
  - remove_game_from_account(game)    (redirect to Steam Support)

All actions connect back to MainWindow for state access and UI updates.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from src.core.game_manager import Game
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class GameActions:
    """Handles all game-specific actions from the context menu.

    Owns no persistent state beyond a reference to MainWindow. Each action
    method delegates to the appropriate parser or manager and triggers the
    standard save/populate cycle when data changes.

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: 'MainWindow') -> None:
        """Initializes the GameActions handler.

        Args:
            main_window: The MainWindow instance that owns these actions.
        """
        self.mw: 'MainWindow' = main_window

    # ------------------------------------------------------------------
    # Public API - Game Actions
    # ------------------------------------------------------------------

    def toggle_favorite(self, game: Game) -> None:
        """Toggles the favorite status of a game.

        Adds or removes the game from the special 'favorites' collection.
        Favorites are stored in cloud-storage-namespace-1.json only.
        Changes are immediately saved and the UI is refreshed.

        Args:
            game: The game to add to or remove from favorites.
        """
        # Check if we have ANY parser available
        if not self.mw.cloud_storage_parser:
            return

        favorites_key = t('ui.categories.favorites')

        if game.is_favorite():
            # Remove from favorites
            if favorites_key in game.categories:
                game.categories.remove(favorites_key)
            # noinspection PyProtectedMember
            self.mw._remove_app_category(game.app_id, favorites_key)
        else:
            # Add to favorites
            if favorites_key not in game.categories:
                game.categories.append(favorites_key)
            # noinspection PyProtectedMember
            self.mw._add_app_category(game.app_id, favorites_key)

        # noinspection PyProtectedMember
        self.mw._save_collections()
        # noinspection PyProtectedMember
        self.mw._populate_categories()

    def toggle_hide_game(self, game: Game, hide: bool) -> None:
        """Toggles the hidden status of a game.

        Hidden games are moved to the special "Hidden" category and
        excluded from other category listings.

        Args:
            game: The game to hide or unhide.
            hide: True to hide the game, False to show it.
        """
        if not self.mw.localconfig_helper:
            return
        self.mw.localconfig_helper.set_app_hidden(game.app_id, hide)

        # noinspection PyProtectedMember
        if self.mw._save_collections():
            game.hidden = hide

            # Refresh UI
            # noinspection PyProtectedMember
            self.mw._populate_categories()

            status_word = t('ui.visibility.hidden') if hide else t('ui.visibility.visible')
            self.mw.set_status(f"{status_word}: {game.name}")

            msg = t('ui.visibility.message', game=game.name, status=status_word)
            UIHelper.show_success(self.mw, msg, t('ui.visibility.title'))

    @staticmethod
    def open_in_store(game: Game) -> None:
        """Opens the Steam Store page for a game in the default browser.

        This is a static method as it doesn't require MainWindow state.

        Args:
            game: The game to view in the store.
        """
        import webbrowser
        webbrowser.open(f"https://store.steampowered.com/app/{game.app_id}")

    def remove_from_local_config(self, game: Game) -> None:
        """Removes a game entry from the local Steam configuration.

        This is useful for removing 'ghost' entries that no longer exist in Steam
        but still appear in localconfig.vdf. Shows a confirmation dialog before
        removing.

        Args:
            game: The game to remove from the local configuration.
        """
        if not UIHelper.confirm(
                self.mw,
                t('ui.dialogs.remove_local_warning', game=game.name),
                t('ui.dialogs.remove_local_title')
        ):
            return

        if self.mw.localconfig_helper:
            success = self.mw.localconfig_helper.remove_app(str(game.app_id))
            if success:
                # noinspection PyProtectedMember
                self.mw._save_collections()

                # Remove from game manager
                if self.mw.game_manager and str(game.app_id) in self.mw.game_manager.games:
                    del self.mw.game_manager.games[str(game.app_id)]

                # Refresh tree
                # noinspection PyProtectedMember
                self.mw._populate_categories()

                UIHelper.show_success(
                    self.mw,
                    t('ui.dialogs.remove_local_success', game=game.name),
                    t('common.success')
                )
            else:
                UIHelper.show_error(self.mw, t('ui.dialogs.remove_local_error'))

    def remove_game_from_account(self, game: Game) -> None:
        """Redirects the user to Steam Support to remove a game from their account.

        Shows a warning dialog before opening the browser, as this action is
        permanent and cannot be undone.

        Args:
            game: The game to remove from the account.
        """
        if UIHelper.confirm(
                self.mw,
                f"{t('emoji.warning')} {t('ui.dialogs.remove_account_warning')}",
                t('ui.dialogs.remove_account_title')
        ):
            import webbrowser
            # Steam Support URL for removing a game (issueid 123 is "remove from account")
            url = f"https://help.steampowered.com/en/wizard/HelpWithGameIssue/?appid={game.app_id}&issueid=123"
            webbrowser.open(url)