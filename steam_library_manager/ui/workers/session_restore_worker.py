#
# steam_library_manager/ui/workers/session_restore_worker.py
# Background worker for Steam session restore (token refresh, validation).
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time as _time
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT_SHORT

logger = logging.getLogger("steamlibmgr.session_restore_worker")

__all__ = ["SessionRestoreResult", "SessionRestoreWorker"]


@dataclass(frozen=True)
class SessionRestoreResult:
    """Immutable result of a session restore attempt."""

    success: bool
    access_token: str | None = None
    refresh_token: str | None = None
    steam_id: str | None = None
    persona_name: str | None = None


class SessionRestoreWorker(QThread):
    """Background thread for restoring a Steam session without blocking the UI."""

    session_restored = pyqtSignal(object)

    def run(self) -> None:
        """Execute the full session restore pipeline."""
        from steam_library_manager.core.token_store import TokenStore, _REFRESH_NOT_NEEDED

        token_store = TokenStore()
        stored = token_store.load_tokens()

        if stored is None:
            self.session_restored.emit(SessionRestoreResult(success=False))
            return

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
                self.session_restored.emit(SessionRestoreResult(success=False))
                return

        persona_name = self.fetch_steam_persona_name(stored.steam_id)

        logger.info(t("logs.auth.token_loaded"))
        self.session_restored.emit(
            SessionRestoreResult(
                success=True,
                access_token=active_token,
                refresh_token=stored.refresh_token,
                steam_id=stored.steam_id,
                persona_name=persona_name,
            )
        )

    @staticmethod
    def fetch_steam_persona_name(steam_id: str) -> str | None:
        """Fetch the public persona name from Steam Community XML."""
        import requests
        import xml.etree.ElementTree as ET

        try:
            url = f"https://steamcommunity.com/profiles/{steam_id}/?xml=1"
            response = requests.get(url, timeout=HTTP_TIMEOUT_SHORT)
            if response.status_code == 200:
                tree = ET.fromstring(response.content)
                steam_id_element = tree.find("steamID")
                if steam_id_element is not None and steam_id_element.text:
                    return steam_id_element.text
        except (requests.RequestException, ET.ParseError) as e:
            logger.error(t("logs.auth.profile_error", error=str(e)))
        except Exception as e:
            logger.error(t("logs.auth.unexpected_profile_error", error=str(e)))

        return None
