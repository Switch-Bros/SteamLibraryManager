"""Action handler for the coordinated 'Enrich All' operation.

Individual enrichment starters (HLTB, Deck, ProtonDB, etc.) live in
enrichment_starters.py.  This module keeps only the composite
start_enrich_all plus shared helper methods.
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
    """Handles the coordinated 'Enrich All' operation.

    Runs tag import followed by parallel enrichment tracks
    (Steam API, HLTB, ProtonDB, Deck, PEGI, Achievements).

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: MainWindow) -> None:
        """Initializes the EnrichmentActions handler.

        Args:
            main_window: The MainWindow instance that owns these actions.
        """
        self.mw: MainWindow = main_window

    def start_enrich_all(self) -> None:
        """Starts a full refresh of all enrichment data.

        Runs tag import followed by four parallel tracks:
        Steam API (metadata + achievements), HLTB, ProtonDB, and Deck.
        """
        from src.config import config
        from src.services.enrichment.enrich_all_coordinator import EnrichAllCoordinator
        from src.ui.dialogs.enrich_all_progress_dialog import EnrichAllProgressDialog

        if not self.mw.game_manager:
            return

        api_key = config.STEAM_API_KEY
        if not api_key:
            UIHelper.show_warning(self.mw, t("ui.enrichment.no_api_key"))
            self._open_settings_api_tab()
            return

        # Resolve Steam user ID
        steam_id = config.STEAM_USER_ID or ""
        if not steam_id:
            _, detected_id = config.get_detected_user()
            if detected_id:
                steam_id = detected_id

        # Get game lists
        all_deck_games = self.mw.game_manager.get_real_games()
        db = self._open_database()
        if db is None:
            return
        all_db_games = db.get_all_game_ids()
        db.close()

        if not all_db_games:
            UIHelper.show_info(self.mw, t("ui.enrichment.no_games_steam"))
            return

        # Confirm with user
        if not UIHelper.confirm(
            self.mw,
            t("ui.enrichment.enrich_all_confirm", count=len(all_db_games)),
            title=t("ui.enrichment.enrich_all_title"),
        ):
            return

        # Check HLTB availability
        hltb_client = None
        try:
            from src.integrations.hltb_api import HLTBClient

            if HLTBClient.is_available():
                hltb_client = HLTBClient()
        except ImportError:
            pass

        # Gather paths and config
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

        # Create dialog and coordinator (coordinator parented to dialog)
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _open_settings_api_tab(self) -> None:
        """Opens the Settings dialog on the API keys tab."""
        from src.ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.mw)
        dialog.tabs.setCurrentIndex(1)
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

        Returns:
            New Database instance, or None if path not available.
        """
        from src.core.database import Database

        db_path = self._get_db_path()
        if db_path is None:
            return None
        return Database(db_path)
