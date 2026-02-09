# src/ui/actions/steam_actions.py

"""
Action handler for Steam menu operations.

Extracts the following methods from MainWindow:
  - start_steam_login()  (initiates Steam OpenID login)
  - show_about()         (shows application About dialog)

The login callbacks (_on_steam_login_success, _on_steam_login_error) remain
in MainWindow as they are connected via Qt signals and directly modify
MainWindow state.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow
    from src.ui.widgets.ui_helper import UIHelper
    from src.config import config


class SteamActions:
    """Handles all Steam menu actions.

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: 'MainWindow') -> None:
        """Initializes the SteamActions handler.

        Args:
            main_window: The MainWindow instance that owns these actions.
        """
        self.mw: 'MainWindow' = main_window

    # ------------------------------------------------------------------
    # Public API - Steam Actions
    # ------------------------------------------------------------------

    def start_steam_login(self) -> None:
        """Initiates the Steam OpenID authentication process.

        Opens an embedded login dialog for Steam login. The actual login
        callbacks (_on_steam_login_success, _on_steam_login_error) are
        handled by MainWindow via Qt signals.
        """
        self.mw.auth_manager.start_login(parent=self.mw)

    def show_about(self) -> None:
        """Shows the About dialog with application information.

        Displays a modal dialog containing the application name and description
        using Qt's standard About box.
        """
        QMessageBox.about(self.mw, t('ui.menu.help.about'), t('app.description'))

    def on_login_success(self, steam_id_64: str) -> None:
        """Handles successful Steam authentication.

        Args:
            steam_id_64: The authenticated user's Steam ID64.
        """
        from src.ui.handlers.data_load_handler import DataLoadHandler

        print(t('logs.auth.login_success', id=steam_id_64))
        self.mw.set_status(t('ui.login.status_success'))
        UIHelper.show_success(self.mw, t('ui.login.status_success'), t('ui.login.title'))

        config.STEAM_USER_ID = steam_id_64
        # Save immediately so login persists after restart
        config.save()

        # Fetch persona name
        self.mw.steam_username = DataLoadHandler.fetch_steam_persona_name(steam_id_64)

        # Update user label
        display_text = self.mw.steam_username if self.mw.steam_username else steam_id_64
        self.mw.user_label.setText(t('ui.main_window.user_label', user_id=display_text))

        # Rebuild toolbar to show name instead of login button
        self.mw.refresh_toolbar()

        if self.mw.game_manager:
            self.mw.data_load_handler.load_games_with_progress(steam_id_64)

    def on_login_error(self, error: str) -> None:
        """Handles Steam authentication errors.

        Args:
            error: The error message from authentication.
        """
        self.mw.set_status(t('ui.login.status_failed'))
        self.mw.reload_btn.show()
        UIHelper.show_error(self.mw, error)