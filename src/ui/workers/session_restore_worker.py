"""Worker thread for restoring Steam session in the background.

This module contains the SessionRestoreWorker that handles all HTTP-blocking
session operations (token refresh, validation, persona fetch) without
blocking the main UI thread.
"""

from __future__ import annotations

import logging
import time as _time
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.session_restore_worker")

__all__ = ["SessionRestoreResult", "SessionRestoreWorker"]


@dataclass(frozen=True)
class SessionRestoreResult:
    """Immutable result of a session restore attempt.

    Attributes:
        success: Whether the session was restored with a valid token.
        access_token: The validated or refreshed access token.
        refresh_token: The refresh token from storage.
        steam_id: SteamID64 of the authenticated user.
        persona_name: Display name fetched from Steam Community.
    """

    success: bool
    access_token: str | None = None
    refresh_token: str | None = None
    steam_id: str | None = None
    persona_name: str | None = None


class SessionRestoreWorker(QThread):
    """Background thread for restoring a Steam session without blocking the UI.

    Performs token loading, refresh with retries, validation fallback,
    and persona name fetch — all in a separate thread.

    Signals:
        session_restored: Emitted with a SessionRestoreResult when done.
    """

    session_restored = pyqtSignal(object)

    def run(self) -> None:
        """Execute the full session restore pipeline.

        Steps:
            1. Load stored tokens from keyring/file (fast).
            2. Try to refresh the access token (HTTP, retries).
            3. If refresh fails, validate the stored token (HTTP).
            4. Fetch persona name from Steam Community (HTTP).
            5. Emit result via signal.
        """
        from src.core.token_store import TokenStore, _REFRESH_NOT_NEEDED

        token_store = TokenStore()
        stored = token_store.load_tokens()

        if stored is None:
            self.session_restored.emit(SessionRestoreResult(success=False))
            return

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
            # Got a fresh token from Steam
            active_token = refresh_result
            token_store.save_tokens(refresh_result, stored.refresh_token, stored.steam_id)
        elif refresh_result == _REFRESH_NOT_NEEDED:
            # Steam returned 200 but no new token — stored token is still valid
            logger.info(t("logs.auth.token_validation_ok"))
            active_token = stored.access_token
        else:
            # Refresh truly failed — validate stored token as fallback
            logger.warning(t("logs.auth.token_refresh_failed", error="using stored token"))
            if TokenStore.validate_access_token(stored.access_token, stored.steam_id):
                logger.info(t("logs.auth.token_validation_ok"))
                active_token = stored.access_token
            else:
                # Both refresh and validation failed — token is expired
                logger.error(t("logs.auth.token_validation_failed"))
                self.session_restored.emit(SessionRestoreResult(success=False))
                return

        # Fetch persona name (HTTP)
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
        """Fetch the public persona name from Steam Community XML.

        Args:
            steam_id: The SteamID64 to look up.

        Returns:
            The persona name if found, otherwise None.
        """
        import requests
        import xml.etree.ElementTree as ET

        try:
            url = f"https://steamcommunity.com/profiles/{steam_id}/?xml=1"
            response = requests.get(url, timeout=5)
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
