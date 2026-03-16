#
# steam_library_manager/ui/actions/steam_actions.py
# Steam login, session restore, and account actions
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

logger = logging.getLogger("steamlibmgr.steam_actions")

__all__ = ["SteamActions"]


class SteamActions:
    """Handles all Steam menu actions."""

    def __init__(self, main_window: "MainWindow") -> None:
        self.mw: "MainWindow" = main_window

    def start_steam_login(self) -> None:
        """Opens the modern Steam login dialog (QR code + password)."""
        from steam_library_manager.ui.dialogs.steam_modern_login_dialog import ModernSteamLoginDialog

        dialog = ModernSteamLoginDialog(parent=self.mw)
        dialog.login_success.connect(self.on_login_success)
        dialog.exec()

    def show_about(self) -> None:
        """Shows the professional About dialog with application information."""
        from steam_library_manager.ui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog(parent=self.mw)
        dialog.exec()

    def check_for_updates(self) -> None:
        """Checks for application updates via GitHub Releases API."""
        from steam_library_manager.services.update_service import UpdateService

        service = UpdateService(parent=self.mw)
        service.update_available.connect(self._on_update_available)
        service.update_not_available.connect(
            lambda: UIHelper.show_info(self.mw, t("update.up_to_date"), t("update.check_title"))
        )
        service.check_failed.connect(lambda msg: UIHelper.show_warning(self.mw, msg, t("update.check_title")))
        self.mw._update_service = service
        service.check_for_update()

    def _on_update_available(self, info: object) -> None:
        """Shows update dialog when a newer version is found."""
        from steam_library_manager.services.update_service import UpdateInfo
        from steam_library_manager.ui.dialogs.update_dialog import UpdateDialog

        if not isinstance(info, UpdateInfo):
            return
        service = getattr(self.mw, "_update_service", None)
        if not service:
            return
        dialog = UpdateDialog(parent=self.mw, info=info, update_service=service)
        dialog.exec()

    def on_login_success(self, result: dict) -> None:
        """Handles successful Steam authentication."""
        from steam_library_manager.core.token_store import TokenStore
        from steam_library_manager.ui.workers.session_restore_worker import SessionRestoreWorker
        from steam_library_manager.config import config

        steam_id_64 = result["steam_id"]

        if result["method"] == "qr":
            logger.info(t("logs.auth.qr_login_success"))
            self.mw.access_token = result.get("access_token")
            self.mw.refresh_token = result.get("refresh_token")
            self.mw.session = None
            config.STEAM_ACCESS_TOKEN = result.get("access_token")
        else:
            logger.info(t("logs.auth.password_login_success"))
            self.mw.session = result.get("session")
            self.mw.access_token = result.get("access_token")
            self.mw.refresh_token = result.get("refresh_token")
            config.STEAM_ACCESS_TOKEN = result.get("access_token")

        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")
        if access_token and refresh_token:
            token_store = TokenStore()
            token_store.save_tokens(access_token, refresh_token, steam_id_64)

        logger.info(t("logs.auth.login_success", id=steam_id_64))
        self.mw.set_status(t("steam.login.status_success"))
        UIHelper.show_success(self.mw, t("steam.login.status_success"), t("steam.login.title"))

        config.STEAM_USER_ID = steam_id_64
        config.save()

        persona = SessionRestoreWorker.fetch_steam_persona_name(steam_id_64)
        self.mw.steam_username = persona or steam_id_64

        display_text = self.mw.steam_username if self.mw.steam_username else steam_id_64
        self.mw.user_label.setText(t("ui.main_window.user_label", user_id=display_text))

        self.mw.refresh_toolbar()

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
        """Restores a previous session from stored tokens (manual trigger)."""
        import time as _time

        from steam_library_manager.core.token_store import TokenStore, _REFRESH_NOT_NEEDED
        from steam_library_manager.ui.workers.session_restore_worker import SessionRestoreWorker
        from steam_library_manager.config import config

        token_store = TokenStore()
        stored = token_store.load_tokens()

        if stored is None:
            return False

        token_age_hours = (_time.time() - stored.timestamp) / 3600
        logger.info(
            t(
                "logs.auth.token_age_info",
                hours=f"{token_age_hours:.1f}",
                timestamp=_time.strftime("%Y-%m-%d %H:%M", _time.localtime(stored.timestamp)),
            )
        )

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
                self.mw.set_status(t("steam.login.token_expired"))
                return False

        self.mw.access_token = active_token
        self.mw.refresh_token = stored.refresh_token
        self.mw.session = None
        config.STEAM_ACCESS_TOKEN = active_token
        config.STEAM_USER_ID = stored.steam_id

        persona = SessionRestoreWorker.fetch_steam_persona_name(stored.steam_id)
        self.mw.steam_username = persona or stored.steam_id

        display_text = self.mw.steam_username or stored.steam_id
        self.mw.user_label.setText(t("ui.main_window.user_label", user_id=display_text))
        self.mw.refresh_toolbar()

        logger.info(t("logs.auth.token_loaded"))
        self.mw.set_status(t("steam.login.session_restored"))

        return True

    def on_login_error(self, error: str) -> None:
        """Handles Steam authentication errors."""
        self.mw.set_status(t("steam.login.status_failed"))
        self.mw.reload_btn.show()
        UIHelper.show_error(self.mw, error)
