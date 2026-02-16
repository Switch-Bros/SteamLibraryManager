"""Action handler for metadata enrichment operations.

Provides start methods for HLTB and Steam API enrichment that check
preconditions, create the EnrichmentThread, and launch the progress dialog.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

logger = logging.getLogger("steamlibmgr.enrichment_actions")

__all__ = ["EnrichmentActions"]


class EnrichmentActions:
    """Handles enrichment-related menu actions.

    Checks preconditions (API keys, library availability, games to enrich)
    and launches the enrichment dialog with a background thread.

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: MainWindow) -> None:
        """Initializes the EnrichmentActions handler.

        Args:
            main_window: The MainWindow instance that owns these actions.
        """
        self.mw: MainWindow = main_window

    def start_deck_enrichment(self) -> None:
        """Starts deck status enrichment for games missing deck data.

        Filters games with no or 'unknown' deck status, then launches
        the DeckEnrichmentThread with a progress dialog.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QProgressDialog

        from src.services.enrichment.deck_enrichment_service import DeckEnrichmentThread

        if not self.mw.game_manager:
            return

        # Filter games missing deck status
        all_games = self.mw.game_manager.get_real_games()
        games_to_enrich = [g for g in all_games if not g.steam_deck_status or g.steam_deck_status == "unknown"]

        if not games_to_enrich:
            UIHelper.show_info(self.mw, t("ui.enrichment.no_games_deck"))
            return

        # Determine cache directory
        from src.config import config

        cache_dir = config.DATA_DIR / "cache"

        # Create thread
        thread = DeckEnrichmentThread(self.mw)
        thread.configure(games_to_enrich, cache_dir)

        # Create progress dialog
        progress = QProgressDialog(
            t("ui.enrichment.deck_starting"),
            t("common.cancel"),
            0,
            len(games_to_enrich),
            self.mw,
        )
        progress.setWindowTitle(t("ui.enrichment.deck_title"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        # Keep references alive
        self._deck_thread = thread
        self._deck_progress = progress

        def on_progress(text: str, current: int, total: int) -> None:
            if progress.wasCanceled():
                thread.cancel()
                return
            progress.setValue(current)
            progress.setLabelText(text)

        def on_finished(success: int, failed: int) -> None:
            progress.close()
            UIHelper.show_success(
                self.mw,
                t("ui.enrichment.deck_complete", success=success, failed=failed),
            )
            self.mw.populate_categories()

        thread.progress.connect(on_progress)
        thread.finished_enrichment.connect(on_finished)
        progress.canceled.connect(thread.cancel)
        thread.start()

    def start_hltb_enrichment(self) -> None:
        """Starts HLTB enrichment for games missing HLTB data.

        Checks that howlongtobeatpy is installed and that there are
        games without HLTB data. Launches the enrichment dialog.
        """
        from src.integrations.hltb_api import HLTBClient
        from src.services.enrichment.enrichment_service import EnrichmentThread
        from src.ui.dialogs.enrichment_dialog import EnrichmentDialog

        # Check library availability
        if not HLTBClient.is_available():
            UIHelper.show_warning(self.mw, t("ui.enrichment.hltb_not_available"))
            return

        # Check database
        db = self._open_database()
        if db is None:
            return

        games = db.get_apps_without_hltb()
        db.close()
        if not games:
            UIHelper.show_info(self.mw, t("ui.enrichment.no_games_hltb"))
            return

        # Create thread with HLTB configuration
        db_path = self._get_db_path()
        hltb_client = HLTBClient()

        thread = EnrichmentThread(self.mw)
        thread.configure_hltb(games, db_path, hltb_client)

        # Create dialog — thread starts in showEvent
        dialog = EnrichmentDialog(t("ui.enrichment.hltb_title"), self.mw)
        dialog.start_thread(thread)
        dialog.exec()

    def start_steam_api_enrichment(self) -> None:
        """Starts Steam API enrichment for games missing metadata.

        Checks that an API key is configured and that there are
        games with missing metadata. Launches the enrichment dialog.
        """
        from src.config import config
        from src.services.enrichment.enrichment_service import EnrichmentThread
        from src.ui.dialogs.enrichment_dialog import EnrichmentDialog

        # Check API key
        api_key = config.STEAM_API_KEY
        if not api_key:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_api_key"))
            self._open_settings_api_tab()
            return

        # Check database
        db = self._open_database()
        if db is None:
            return

        games = db.get_apps_missing_metadata()
        db.close()
        if not games:
            UIHelper.show_info(self.mw, t("ui.enrichment.no_games_steam"))
            return

        # Create thread with Steam API configuration
        db_path = self._get_db_path()

        thread = EnrichmentThread(self.mw)
        thread.configure_steam(games, db_path, api_key)

        # Create dialog — thread starts in showEvent
        dialog = EnrichmentDialog(t("ui.enrichment.steam_title"), self.mw)
        dialog.start_thread(thread)
        dialog.exec()

    def start_achievement_enrichment(self) -> None:
        """Starts achievement enrichment for games missing achievement data.

        Checks that an API key and Steam ID are configured, then launches
        the AchievementEnrichmentThread with a progress dialog.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QProgressDialog

        from src.config import config
        from src.services.enrichment.achievement_enrichment_service import AchievementEnrichmentThread

        # Check API key
        api_key = config.STEAM_API_KEY
        if not api_key:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_api_key"))
            self._open_settings_api_tab()
            return

        # Check Steam user ID
        steam_id = config.STEAM_USER_ID
        if not steam_id:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_steam_id"))
            return

        # Check database
        db = self._open_database()
        if db is None:
            return

        games = db.get_apps_without_achievements()
        db.close()
        if not games:
            UIHelper.show_info(self.mw, t("ui.enrichment.no_games_achievements"))
            return

        # Create thread
        db_path = self._get_db_path()
        thread = AchievementEnrichmentThread(self.mw)
        thread.configure(games, db_path, api_key, steam_id)

        # Create progress dialog
        progress = QProgressDialog(
            t("ui.enrichment.achievement_starting"),
            t("common.cancel"),
            0,
            len(games),
            self.mw,
        )
        progress.setWindowTitle(t("ui.enrichment.achievement_title"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        # Keep references alive
        self._achievement_thread = thread
        self._achievement_progress = progress

        def on_progress(text: str, current: int, total: int) -> None:
            if progress.wasCanceled():
                thread.cancel()
                return
            progress.setValue(current)
            progress.setLabelText(text)

        def on_finished(success_count: int, failed_count: int) -> None:
            progress.close()
            UIHelper.show_success(
                self.mw,
                t("ui.enrichment.achievement_complete", success=success_count, failed=failed_count),
            )
            self.mw.populate_categories()

        thread.progress.connect(on_progress)
        thread.finished_enrichment.connect(on_finished)
        progress.canceled.connect(thread.cancel)
        thread.start()

    def _open_settings_api_tab(self) -> None:
        """Opens the Settings dialog on the API keys tab."""
        from src.ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.mw)
        dialog.tabs.setCurrentIndex(1)  # "Other" tab with API keys
        dialog.settings_saved.connect(self.mw.settings_actions.apply_settings)
        dialog.exec()

    def _get_db_path(self):
        """Returns the database file path from the active game service.

        Returns:
            Path to the SQLite database, or None if not available.
        """
        if hasattr(self.mw, "game_service") and self.mw.game_service:
            db = getattr(self.mw.game_service, "database", None)
            if db and hasattr(db, "db_path"):
                return db.db_path

        logger.warning("No database available for enrichment")
        return None

    def _open_database(self):
        """Opens a fresh database connection for enrichment operations.

        Creates a new Database instance to avoid SQLite threading issues,
        since the main database may have been created in a different thread.

        Returns:
            New Database instance, or None if path not available.
        """
        from src.core.database import Database

        db_path = self._get_db_path()
        if db_path is None:
            return None
        return Database(db_path)
