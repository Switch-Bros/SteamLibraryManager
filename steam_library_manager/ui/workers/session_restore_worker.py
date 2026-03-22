#
# steam_library_manager/ui/workers/session_restore_worker.py
# Background QThread worker for restoring the previous UI session
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: retry logic is messy, refactor later

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
    """Result of session restore attempt."""

    success: bool
    access_token: str | None = None
    refresh_token: str | None = None
    steam_id: str | None = None
    persona_name: str | None = None


class SessionRestoreWorker(QThread):
    """Background thread for Steam session restore."""

    session_restored = pyqtSignal(object)

    def run(self):
        # full restore pipeline
        from steam_library_manager.core.token_store import TokenStore, _REFRESH_NOT_NEEDED

        ts = TokenStore()
        stored = ts.load_tokens()

        if stored is None:
            self.session_restored.emit(SessionRestoreResult(success=False))
            return

        # log token age
        age_hours = (_time.time() - stored.timestamp) / 3600
        logger.info(
            t(
                "logs.auth.token_age_info",
                hours="%.1f" % age_hours,
                timestamp=_time.strftime("%Y-%m-%d %H:%M", _time.localtime(stored.timestamp)),
            )
        )

        # try refresh with retry
        refresh_result = ts.refresh_access_token(stored.refresh_token, stored.steam_id)

        if refresh_result and refresh_result != _REFRESH_NOT_NEEDED:
            # got fresh token
            active_token = refresh_result
            ts.save_tokens(refresh_result, stored.refresh_token, stored.steam_id)
        elif refresh_result == _REFRESH_NOT_NEEDED:
            # steam returned 200 but no new token - still valid
            logger.info(t("logs.auth.token_validation_ok"))
            active_token = stored.access_token
        else:
            # refresh failed - validate stored token as fallback
            logger.warning(t("logs.auth.token_refresh_failed", error="using stored token"))
            if TokenStore.validate_access_token(stored.access_token, stored.steam_id):
                logger.info(t("logs.auth.token_validation_ok"))
                active_token = stored.access_token
            else:
                # both failed - expired
                logger.error(t("logs.auth.token_validation_failed"))
                self.session_restored.emit(SessionRestoreResult(success=False))
                return

        # fetch persona name via HTTP
        name = self.fetch_steam_persona_name(stored.steam_id)

        logger.info(t("logs.auth.token_loaded"))
        self.session_restored.emit(
            SessionRestoreResult(
                success=True,
                access_token=active_token,
                refresh_token=stored.refresh_token,
                steam_id=stored.steam_id,
                persona_name=name,
            )
        )

    @staticmethod
    def fetch_steam_persona_name(sid: str):
        # grab display name from steam community xml
        # FIXME: XML parsing is fragile
        import requests
        import xml.etree.ElementTree as ET

        try:
            url = "https://steamcommunity.com/profiles/%s/?xml=1" % sid
            resp = requests.get(url, timeout=HTTP_TIMEOUT_SHORT)
            if resp.status_code == 200:
                tree = ET.fromstring(resp.content)
                el = tree.find("steamID")
                if el is not None and el.text:
                    return el.text
        except (requests.RequestException, ET.ParseError) as e:
            logger.error(t("logs.auth.profile_error", error=str(e)))
        except Exception as e:
            logger.error(t("logs.auth.unexpected_profile_error", error=str(e)))

        return None
