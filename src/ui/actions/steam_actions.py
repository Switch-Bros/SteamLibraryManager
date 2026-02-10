# src/ui/actions/steam_actions.py

"""
Action handler for Steam menu operations.

Handles Steam login with modern QR code + Username/Password dialog.
NO MORE OpenID! Full 2FA support with session cookies and access tokens.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict

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
        """Initiates the modern Steam login process.

        Opens a modern login dialog with QR code + Username/Password options.
        Supports full 2FA, email verification, and CAPTCHA.

        NO API KEY NEEDED! Uses session cookies or OAuth tokens.
        """
        from src.ui.steam_modern_login_dialog import ModernSteamLoginDialog

        dialog = ModernSteamLoginDialog(parent=self.mw)
        dialog.login_success.connect(self.on_login_success)
        dialog.exec()

    def show_about(self) -> None:
        """Shows the About dialog with application information.

        Displays a modal dialog containing the application name and description
        using Qt's standard About box.
        """
        QMessageBox.about(self.mw, t('ui.menu.help.about'), t('app.description'))

    def on_login_success(self, result: Dict) -> None:
        """Handles successful Steam authentication.

        Args:
            result: Login result dict containing:
                - method: 'qr' or 'password'
                - steam_id: SteamID64
                - access_token: (if QR login)
                - refresh_token: (if QR login)
                - session: (if password login)
                - account_name: (optional)
        """
        from src.ui.handlers.data_load_handler import DataLoadHandler
        from src.ui.widgets.ui_helper import UIHelper
        from src.config import config

        steam_id_64 = result['steam_id']

        # Store session/token for API access
        if result['method'] == 'qr':
            # Log QR login success (using existing key)
            token_preview = result.get('access_token', '')[:20] if result.get('access_token') else ''
            print(f"QR Login successful! Token: {token_preview}...")
            self.mw.access_token = result.get('access_token')
            self.mw.refresh_token = result.get('refresh_token')
            self.mw.session = None
        else:  # password login
            # Log password login success
            print("Password login successful! Session cookies stored.")
            self.mw.session = result.get('session')
            self.mw.access_token = None
            self.mw.refresh_token = None

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

        # Load games using new session/token method
        if self.mw.game_service and self.mw.game_service.game_manager:
            try:
                self.mw.data_load_handler.load_games_with_steam_login(
                    steam_id_64,
                    self.mw.session or self.mw.access_token
                )
            except Exception as e:
                # Log error (console only, not user-facing)
                print(f"Error loading games: {str(e)}")
                # Show user-facing error with existing key
                UIHelper.show_error(
                    self.mw,
                    t('logs.auth.error', error=str(e))
                )
        else:
            # Game service not ready yet (should not happen normally)
            print("Warning: game_service not initialized yet")

    def on_login_error(self, error: str) -> None:
        """Handles Steam authentication errors.

        Args:
            error: The error message from authentication.
        """
        self.mw.set_status(t('ui.login.status_failed'))
        self.mw.reload_btn.show()
        UIHelper.show_error(self.mw, error)