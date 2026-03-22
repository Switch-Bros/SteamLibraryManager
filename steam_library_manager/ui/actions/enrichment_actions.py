#
# steam_library_manager/ui/actions/enrichment_actions.py
# UI action handlers for enrichment menu and toolbar operations
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

logger = logging.getLogger("steamlibmgr.enrichment_actions")

__all__ = ["EnrichmentActions"]


class EnrichmentActions:
    """Coordinates full enrichment run (tags + metadata)."""

    def __init__(self, main_window: MainWindow):
        # keep ref to main window
        self.mw = main_window

    def start_enrich_all(self):
        # start full refresh of all enrichment data
        from steam_library_manager.config import config
        from steam_library_manager.services.enrichment.enrich_all_coordinator import EnrichAllCoordinator
        from steam_library_manager.ui.dialogs.enrich_all_progress_dialog import EnrichAllProgressDialog

        if not self.mw.game_manager:
            return

        api_key = config.STEAM_API_KEY
        if not api_key:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_api_key"))
            self._open_settings_api_tab()
            return

        # resolve Steam user ID
        steam_id = config.STEAM_USER_ID or ""
        if not steam_id:
            _, detected_id = config.get_detected_user()
            if detected_id:
                steam_id = detected_id

        # get game lists
        all_deck_games = self.mw.game_manager.get_real_games()
        db = self._open_database()
        if db is None:
            return
        all_db_games = db.get_all_game_ids()
        db.close()

        if not all_db_games:
            UIHelper.show_info(self.mw, t("ui.enrichment.no_games_steam"))
            return

        # confirm with user
        msg = t("ui.enrichment.enrich_all_confirm", count=len(all_db_games))
        title = t("ui.enrichment.enrich_all_title")
        if not UIHelper.confirm(self.mw, msg, title=title):
            return

        # check HLTB availability
        hltb_client = None
        try:
            from steam_library_manager.integrations.hltb_api import HLTBClient

            if HLTBClient.is_available():
                hltb_client = HLTBClient()
        except ImportError:
            pass  # HLTB not installed, whatever

        # gather paths and config
        db_path = self._get_db_path()
        if db_path is None:
            return

        steam_path = config.STEAM_PATH
        cache_dir = config.DATA_DIR / "cache"

        language = "en"
        if hasattr(self.mw, "tag_resolver") and self.mw.tag_resolver:
            i18n = getattr(self.mw, "_i18n", None)
            if i18n:
                language = i18n.locale

        # create dialog and coordinator
        dialog = EnrichAllProgressDialog(self.mw)
        coordinator = EnrichAllCoordinator(dialog)
        coordinator.configure(
            db_path=db_path,
            api_key=api_key,
            steam_id=steam_id,
            steam_path=steam_path,
            games_deck=all_deck_games,
            games_db=all_db_games,
            hltb_client=hltb_client,
            language=language,
            cache_dir=cache_dir,
            games_pegi=all_db_games,
        )

        dialog.set_coordinator(coordinator)
        dialog.exec()

        self.mw.populate_categories()

    def _open_settings_api_tab(self):
        # open settings on API tab
        from steam_library_manager.ui.dialogs.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self.mw)
        dlg.tabs.setCurrentIndex(1)
        dlg.settings_saved.connect(self.mw.settings_actions.apply_settings)
        dlg.exec()

    def _get_db_path(self):
        # get database path from game service
        if hasattr(self.mw, "game_service") and self.mw.game_service:
            db = getattr(self.mw.game_service, "database", None)
            if db and hasattr(db, "db_path"):
                return db.db_path

        logger.warning("No database available for enrichment")
        return None

    def _open_database(self):
        # open fresh db connection
        from steam_library_manager.core.database import Database

        db_path = self._get_db_path()
        if db_path is None:
            return None
        return Database(db_path)
