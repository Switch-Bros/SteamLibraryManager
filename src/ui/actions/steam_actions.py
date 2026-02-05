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
