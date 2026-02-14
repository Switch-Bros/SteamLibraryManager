"""Handler for data loading operations.

This module contains the DataLoadHandler that manages game loading
after Steam login. The initial startup loading is now handled by
BootstrapService; this handler is kept for post-login reloads.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.config import config
from src.integrations.steam_store import SteamStoreScraper
from src.ui.widgets.ui_helper import UIHelper
from src.ui.workers import GameLoadWorker
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.data_load_handler")

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

__all__ = ["DataLoadHandler"]


class DataLoadHandler:
    """Handler for post-login data loading operations.

    Manages game reloading after Steam login using inline progress
    (no modal dialog). The initial startup is handled by BootstrapService.

    Attributes:
        mw: Reference to the MainWindow instance.
        load_worker: Worker thread for async game loading.
    """

    def __init__(self, main_window: MainWindow) -> None:
        """Initialize the data load handler.

        Args:
            main_window: The MainWindow instance.
        """
        self.mw = main_window
        self.load_worker: GameLoadWorker | None = None

    def load_games_with_steam_login(self, steam_id: str, session_or_token) -> None:
        """Load games after Steam login with access token or session.

        This method is called after successful Steam authentication to reload
        the game library with Steam Web API access. Uses inline progress
        instead of a modal dialog.

        Args:
            steam_id: The Steam ID64 of the authenticated user.
            session_or_token: Either a requests.Session or access_token string.
        """
        logger.info(t("logs.auth.loading_games_after_login"))

        if isinstance(session_or_token, str):
            logger.info(t("logs.auth.auth_mode_token"))
        else:
            logger.info(t("logs.auth.auth_mode_session"))

        # Use bootstrap service for non-blocking reload
        if hasattr(self.mw, "bootstrap_service") and self.mw.bootstrap_service:
            self.mw.bootstrap_service.start()
        else:
            # Fallback: direct worker launch with inline progress
            self._load_games_with_progress(steam_id)

    def _load_games_with_progress(self, user_id: str) -> None:
        """Start game loading with inline progress updates.

        Args:
            user_id: The Steam user ID to load games for.
        """
        if not self.mw.game_service:
            logger.error("GameService not initialized, cannot load games")
            return

        # Show inline loading state
        self.mw.tree.set_loading_state(True)

        self.load_worker = GameLoadWorker(self.mw.game_service, user_id)
        self.load_worker.progress_update.connect(self._on_load_progress)
        self.load_worker.finished.connect(self._on_load_finished)
        self.load_worker.start()

    def _on_load_progress(self, step: str, current: int, total: int) -> None:
        """Update the inline progress bar during game loading.

        Args:
            step: Description of the current loading step.
            current: Current progress count.
            total: Total items to process.
        """
        if hasattr(self.mw, "loading_label"):
            self.mw.loading_label.setText(step)
            self.mw.loading_label.setVisible(True)
        if hasattr(self.mw, "progress_bar") and total > 0:
            percent = int((current / total) * 100)
            self.mw.progress_bar.setValue(percent)
            self.mw.progress_bar.setVisible(True)

    def _on_load_finished(self, success: bool) -> None:
        """Handle completion of the game loading process.

        Args:
            success: Whether loading completed successfully.
        """
        # Hide inline progress
        if hasattr(self.mw, "loading_label"):
            self.mw.loading_label.setVisible(False)
        if hasattr(self.mw, "progress_bar"):
            self.mw.progress_bar.setVisible(False)

        # Get game_manager reference from game_service
        self.mw.game_manager = self.mw.game_service.game_manager if self.mw.game_service else None

        if not success or not self.mw.game_manager or not self.mw.game_manager.games:
            UIHelper.show_warning(self.mw, t("ui.errors.no_games_found"))
            self.mw.reload_btn.show()
            self.mw.set_status(t("common.error"))
            return

        # Initialize SteamStoreScraper (lightweight, no I/O)
        self.mw.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)

        # Set appinfo_manager reference (already loaded by worker)
        self.mw.appinfo_manager = self.mw.game_service.appinfo_manager

        # Initialize CategoryService
        from src.services.category_service import CategoryService

        self.mw.category_service = CategoryService(
            localconfig_helper=self.mw.localconfig_helper,
            cloud_parser=self.mw.cloud_storage_parser,
            game_manager=self.mw.game_manager,
        )

        # Initialize MetadataService
        from src.services.metadata_service import MetadataService

        self.mw.metadata_service = MetadataService(
            appinfo_manager=self.mw.appinfo_manager,
            game_manager=self.mw.game_manager,
        )

        # Initialize AutoCategorizeService
        from src.services.autocategorize_service import AutoCategorizeService

        self.mw.autocategorize_service = AutoCategorizeService(
            game_manager=self.mw.game_manager,
            category_service=self.mw.category_service,
            steam_scraper=self.mw.steam_scraper,
        )

        self.mw.populate_categories()

        status_msg = self.mw.game_manager.get_load_source_message()
        self.mw.set_status(status_msg)
        self.mw.reload_btn.hide()
        self.mw.update_statistics()
