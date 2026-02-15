"""Action handler for metadata enrichment operations.

Provides start methods for HLTB and Steam API enrichment that check
preconditions, create the background worker/thread, and launch the
enrichment dialog.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread

from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

logger = logging.getLogger("steamlibmgr.enrichment_actions")

__all__ = ["EnrichmentActions"]


class EnrichmentActions:
    """Handles enrichment-related menu actions.

    Checks preconditions (API keys, library availability, games to enrich)
    and launches the enrichment dialog with a background worker.

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: MainWindow) -> None:
        """Initializes the EnrichmentActions handler.

        Args:
            main_window: The MainWindow instance that owns these actions.
        """
        self.mw: MainWindow = main_window

    def start_hltb_enrichment(self) -> None:
        """Starts HLTB enrichment for games missing HLTB data.

        Checks that howlongtobeatpy is installed and that there are
        games without HLTB data. Launches the enrichment dialog.
        """
        from src.integrations.hltb_api import HLTBClient
        from src.services.enrichment_service import EnrichmentWorker
        from src.ui.dialogs.enrichment_dialog import EnrichmentDialog

        # Check library availability
        if not HLTBClient.is_available():
            UIHelper.show_warning(self.mw, t("ui.enrichment.hltb_not_available"))
            return

        # Check database
        db = self._get_database()
        if db is None:
            return

        games = db.get_apps_without_hltb()
        if not games:
            UIHelper.show_info(self.mw, t("ui.enrichment.no_games_hltb"))
            return

        # Create worker and thread
        worker = EnrichmentWorker()
        thread = QThread()
        worker.moveToThread(thread)

        hltb_client = HLTBClient()

        # Connect thread started to worker method
        thread.started.connect(lambda: worker.run_hltb_enrichment(games, db, hltb_client))

        # Create and show dialog
        dialog = EnrichmentDialog(t("ui.enrichment.hltb_title"), self.mw)
        dialog.start_worker(worker, thread)
        dialog.exec()

    def start_steam_api_enrichment(self) -> None:
        """Starts Steam API enrichment for games missing metadata.

        Checks that an API key is configured and that there are
        games with missing metadata. Launches the enrichment dialog.
        """
        from src.config import config
        from src.services.enrichment_service import EnrichmentWorker
        from src.ui.dialogs.enrichment_dialog import EnrichmentDialog

        # Check API key
        api_key = config.STEAM_API_KEY
        if not api_key:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_api_key"))
            self._open_settings_api_tab()
            return

        # Check database
        db = self._get_database()
        if db is None:
            return

        games = db.get_apps_missing_metadata()
        if not games:
            UIHelper.show_info(self.mw, t("ui.enrichment.no_games_steam"))
            return

        # Create worker and thread
        worker = EnrichmentWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(lambda: worker.run_steam_api_enrichment(games, db, api_key))

        # Create and show dialog
        dialog = EnrichmentDialog(t("ui.enrichment.steam_title"), self.mw)
        dialog.start_worker(worker, thread)
        dialog.exec()

    def _open_settings_api_tab(self) -> None:
        """Opens the Settings dialog on the API keys tab."""
        from src.ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.mw)
        dialog.tabs.setCurrentIndex(1)  # "Other" tab with API keys
        if dialog.exec():
            self.mw.settings_actions.apply_settings(dialog.get_settings())

    def _get_database(self):
        """Returns the active database instance or shows an error.

        Returns:
            Database instance, or None if not available.
        """
        if hasattr(self.mw, "game_service") and self.mw.game_service:
            db = getattr(self.mw.game_service, "db", None)
            if db:
                return db

        # Fallback: try to get from game_manager
        if self.mw.game_manager and hasattr(self.mw.game_manager, "db"):
            return self.mw.game_manager.db

        logger.warning("No database available for enrichment")
        return None
