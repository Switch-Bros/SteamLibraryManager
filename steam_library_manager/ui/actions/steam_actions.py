#
# steam_library_manager/ui/actions/steam_actions.py
# UI action handlers for Steam login, logout, and sync
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import logging

from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.steam_actions")

__all__ = ["SteamActions"]


class SteamActions:
    """Handles Steam menu actions like login, session restore,
    update checks, and the about dialog.
    """

    def __init__(self, main_window):
        self.mw = main_window

    # ------------------------------------------------------------------
    # Public API - Steam Actions
    # ------------------------------------------------------------------

    def start_steam_login(self):
        # Open the modern login dialog (QR + password options)
        from steam_library_manager.ui.dialogs.steam_modern_login_dialog import ModernSteamLoginDialog

        dialog = ModernSteamLoginDialog(parent=self.mw)
        dialog.login_success.connect(self.on_login_success)
        dialog.exec()

    def show_about(self):
        from steam_library_manager.ui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog(parent=self.mw)
        dialog.exec()

    def check_for_updates(self):
        # Check GitHub Releases for a newer version
        from steam_library_manager.services.update_service import UpdateService

        svc = UpdateService(parent=self.mw)
        svc.update_available.connect(self._on_update)
        svc.update_not_available.connect(
            lambda: UIHelper.show_info(self.mw, t("update.up_to_date"), t("update.check_title"))
        )
        svc.check_failed.connect(lambda msg: UIHelper.show_warning(self.mw, msg, t("update.check_title")))
        # Keep reference to prevent GC
        self.mw._update_service = svc
        svc.check_for_update()

    def _on_update(self, info):
        # Show update dialog when a newer version is found
        from steam_library_manager.services.update_service import UpdateInfo
        from steam_library_manager.ui.dialogs.update_dialog import UpdateDialog

        if not isinstance(info, UpdateInfo):
            return
        svc = getattr(self.mw, "_update_service", None)
        if not svc:
            return
        dialog = UpdateDialog(parent=self.mw, info=info, update_service=svc)
        dialog.exec()

    def on_login_success(self, result):
        # Handle successful Steam authentication
        from steam_library_manager.core.token_store import TokenStore
        from steam_library_manager.ui.workers.session_restore_worker import SessionRestoreWorker
        from steam_library_manager.config import config

        steam_id = result["steam_id"]

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
        acc_tok = result.get("access_token")
        ref_tok = result.get("refresh_token")
        if acc_tok and ref_tok:
            store = TokenStore()
            store.save_tokens(acc_tok, ref_tok, steam_id)

        logger.info(t("logs.auth.login_success", id=steam_id))
        self.mw.set_status(t("steam.login.status_success"))
        UIHelper.show_success(self.mw, t("steam.login.status_success"), t("steam.login.title"))

        config.STEAM_USER_ID = steam_id
        config.save()

        # Fetch persona name
        persona = SessionRestoreWorker.fetch_steam_persona_name(steam_id)
        self.mw.steam_username = persona or steam_id

        # Update user label
        display = self.mw.steam_username if self.mw.steam_username else steam_id
        self.mw.user_label.setText(t("ui.main_window.user_label", user_id=display))

        # Rebuild toolbar to show name instead of login button
        self.mw.refresh_toolbar()

        # Reload games via BootstrapService (non-blocking)
        if hasattr(self.mw, "bootstrap_service") and self.mw.bootstrap_service:
            self.mw.bootstrap_service.start()
        elif self.mw.data_load_handler:
            try:
                self.mw.data_load_handler.load_games_with_steam_login(steam_id, self.mw.session or self.mw.access_token)
            except Exception as exc:
                logger.error(t("logs.auth.load_games_error", error=str(exc)))
                UIHelper.show_error(self.mw, t("logs.auth.error", error=str(exc)))

    def restore_session(self):
        # Try to restore a previous session from stored tokens
        import time as _time

        from steam_library_manager.core.token_store import TokenStore, _REFRESH_NOT_NEEDED
        from steam_library_manager.ui.workers.session_restore_worker import SessionRestoreWorker
        from steam_library_manager.config import config

        store = TokenStore()
        stored = store.load_tokens()

        if stored is None:
            return False

        # Log token age for diagnostics
        age_hrs = (_time.time() - stored.timestamp) / 3600
        logger.info(
            t(
                "logs.auth.token_age_info",
                hours="%.1f" % age_hrs,
                timestamp=_time.strftime("%Y-%m-%d %H:%M", _time.localtime(stored.timestamp)),
            )
        )

        # Try to refresh the access token (with retry)
        refreshed = store.refresh_access_token(stored.refresh_token, stored.steam_id)

        if refreshed and refreshed != _REFRESH_NOT_NEEDED:
            active = refreshed
            store.save_tokens(refreshed, stored.refresh_token, stored.steam_id)
        elif refreshed == _REFRESH_NOT_NEEDED:
            logger.info(t("logs.auth.token_validation_ok"))
            active = stored.access_token
        else:
            logger.warning(t("logs.auth.token_refresh_failed", error="using stored token"))
            if TokenStore.validate_access_token(stored.access_token, stored.steam_id):
                logger.info(t("logs.auth.token_validation_ok"))
                active = stored.access_token
            else:
                logger.error(t("logs.auth.token_validation_failed"))
                self.mw.set_status(t("steam.login.token_expired"))
                return False

        # Restore authenticated state
        self.mw.access_token = active
        self.mw.refresh_token = stored.refresh_token
        self.mw.session = None
        config.STEAM_ACCESS_TOKEN = active
        config.STEAM_USER_ID = stored.steam_id

        # Fetch persona name
        persona = SessionRestoreWorker.fetch_steam_persona_name(stored.steam_id)
        self.mw.steam_username = persona or stored.steam_id

        display = self.mw.steam_username or stored.steam_id
        self.mw.user_label.setText(t("ui.main_window.user_label", user_id=display))
        self.mw.refresh_toolbar()

        logger.info(t("logs.auth.token_loaded"))
        self.mw.set_status(t("steam.login.session_restored"))

        return True

    def on_login_error(self, error):
        self.mw.set_status(t("steam.login.status_failed"))
        self.mw.reload_btn.show()
        UIHelper.show_error(self.mw, error)
