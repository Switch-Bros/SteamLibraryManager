# src/ui/actions/steam_actions.py

"""
Action handler for Steam menu operations.

Handles Steam login with modern QR code + Username/Password dialog.
NO MORE OpenID! Full 2FA support with session cookies and access tokens.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow
    from src.ui.widgets.ui_helper import UIHelper

logger = logging.getLogger("steamlibmgr.steam_actions")


class SteamActions:
    """Handles all Steam menu actions.

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initializes the SteamActions handler.

        Args:
            main_window: The MainWindow instance that owns these actions.
        """
        self.mw: "MainWindow" = main_window

    # ------------------------------------------------------------------
    # Public API - Steam Actions
    # ------------------------------------------------------------------

    def start_steam_login(self) -> None:
        """Initiates the modern Steam login process.

        Opens a modern login dialog with QR code + Username/Password options.
        Supports full 2FA, email verification, and CAPTCHA.

        NO API KEY NEEDED! Uses session cookies or OAuth tokens.
        """
        from src.ui.dialogs.steam_modern_login_dialog import ModernSteamLoginDialog

        dialog = ModernSteamLoginDialog(parent=self.mw)
        dialog.login_success.connect(self.on_login_success)
        dialog.exec()

    def show_about(self) -> None:
        """Shows the About dialog with application information.

        Displays a modal dialog containing the application name and description
        using Qt's standard About box.
        """
        QMessageBox.about(self.mw, t("menu.help.about"), t("app.description"))

    def on_login_success(self, result: dict) -> None:
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
        from src.core.token_store import TokenStore
        from src.ui.workers.session_restore_worker import SessionRestoreWorker
        from src.ui.widgets.ui_helper import UIHelper
        from src.config import config

        steam_id_64 = result["steam_id"]

        # Store session/token for API access
        if result["method"] == "qr":
            logger.info(t("logs.auth.qr_login_success"))
            self.mw.access_token = result.get("access_token")
            self.mw.refresh_token = result.get("refresh_token")
            self.mw.session = None
            config.STEAM_ACCESS_TOKEN = result.get("access_token")
        else:  # password login
            logger.info(t("logs.auth.password_login_success"))
            self.mw.session = result.get("session")
            self.mw.access_token = result.get("access_token")
            self.mw.refresh_token = result.get("refresh_token")
            config.STEAM_ACCESS_TOKEN = result.get("access_token")

        # Persist tokens securely for session restore on next startup
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")
        if access_token and refresh_token:
            token_store = TokenStore()
            token_store.save_tokens(access_token, refresh_token, steam_id_64)

        logger.info(t("logs.auth.login_success", id=steam_id_64))
        self.mw.set_status(t("ui.login.status_success"))
        UIHelper.show_success(self.mw, t("ui.login.status_success"), t("ui.login.title"))

        config.STEAM_USER_ID = steam_id_64
        config.save()

        # Fetch persona name
        persona = SessionRestoreWorker.fetch_steam_persona_name(steam_id_64)
        self.mw.steam_username = persona or steam_id_64

        # Update user label
        display_text = self.mw.steam_username if self.mw.steam_username else steam_id_64
        self.mw.user_label.setText(t("ui.main_window.user_label", user_id=display_text))

        # Rebuild toolbar to show name instead of login button
        self.mw.refresh_toolbar()

        # Reload games via BootstrapService (non-blocking)
        if hasattr(self.mw, "bootstrap_service") and self.mw.bootstrap_service:
            self.mw.bootstrap_service.start()
        elif self.mw.data_load_handler:
            try:
                self.mw.data_load_handler.load_games_with_steam_login(
                    steam_id_64, self.mw.session or self.mw.access_token
                )
            except Exception as e:
                logger.error(t("logs.auth.load_games_error", error=str(e)))
                UIHelper.show_error(self.mw, t("logs.auth.error", error=str(e)))

    def restore_session(self) -> bool:
        """Attempt to restore a previous session from securely stored tokens.

        NOTE: At startup, BootstrapService handles session restore in the
        background via SessionRestoreWorker. This method is kept for manual
        session restore actions (e.g. from a menu action).

        Returns:
            True if session was restored with a valid token.
        """
        import time as _time

        from src.core.token_store import TokenStore, _REFRESH_NOT_NEEDED
        from src.ui.workers.session_restore_worker import SessionRestoreWorker
        from src.config import config

        token_store = TokenStore()
        stored = token_store.load_tokens()

        if stored is None:
            return False

        # Log token age for diagnostics
        token_age_hours = (_time.time() - stored.timestamp) / 3600
        logger.info(
            t(
                "logs.auth.token_age_info",
                hours=f"{token_age_hours:.1f}",
                timestamp=_time.strftime("%Y-%m-%d %H:%M", _time.localtime(stored.timestamp)),
            )
        )

        # Try to refresh the access token (with retry)
        refresh_result = token_store.refresh_access_token(stored.refresh_token, stored.steam_id)

        if refresh_result and refresh_result != _REFRESH_NOT_NEEDED:
            active_token = refresh_result
            token_store.save_tokens(refresh_result, stored.refresh_token, stored.steam_id)
        elif refresh_result == _REFRESH_NOT_NEEDED:
            logger.info(t("logs.auth.token_validation_ok"))
            active_token = stored.access_token
        else:
            logger.warning(t("logs.auth.token_refresh_failed", error="using stored token"))
            if TokenStore.validate_access_token(stored.access_token, stored.steam_id):
                logger.info(t("logs.auth.token_validation_ok"))
                active_token = stored.access_token
            else:
                logger.error(t("logs.auth.token_validation_failed"))
                self.mw.set_status(t("ui.login.token_expired"))
                return False

        # Restore authenticated state
        self.mw.access_token = active_token
        self.mw.refresh_token = stored.refresh_token
        self.mw.session = None
        config.STEAM_ACCESS_TOKEN = active_token
        config.STEAM_USER_ID = stored.steam_id

        # Fetch persona name
        persona = SessionRestoreWorker.fetch_steam_persona_name(stored.steam_id)
        self.mw.steam_username = persona or stored.steam_id

        display_text = self.mw.steam_username or stored.steam_id
        self.mw.user_label.setText(t("ui.main_window.user_label", user_id=display_text))
        self.mw.refresh_toolbar()

        logger.info(t("logs.auth.token_loaded"))
        self.mw.set_status(t("ui.login.session_restored"))

        return True

    def on_login_error(self, error: str) -> None:
        """Handles Steam authentication errors.

        Args:
            error: The error message from authentication.
        """
        self.mw.set_status(t("ui.login.status_failed"))
        self.mw.reload_btn.show()
        UIHelper.show_error(self.mw, error)
