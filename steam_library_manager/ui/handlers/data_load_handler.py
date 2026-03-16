#
# steam_library_manager/ui/handlers/data_load_handler.py
# Handler for post-login game data loading.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from steam_library_manager.config import config
from steam_library_manager.integrations.steam_store import SteamStoreScraper
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.ui.workers import GameLoadWorker
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.data_load_handler")

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["DataLoadHandler"]


class DataLoadHandler:
    """Manages game reloading after Steam login using inline progress."""

    def __init__(self, main_window: MainWindow) -> None:
        self.mw = main_window
        self.load_worker: GameLoadWorker | None = None

    def load_games_with_steam_login(self, steam_id: str, session_or_token) -> None:
        """Reload game library after successful Steam authentication."""
        logger.info(t("logs.auth.loading_games_after_login"))

        if isinstance(session_or_token, str):
            logger.info(t("logs.auth.auth_mode_token"))
        else:
            logger.info(t("logs.auth.auth_mode_session"))

        if hasattr(self.mw, "bootstrap_service") and self.mw.bootstrap_service:
            self.mw.bootstrap_service.start()
        else:
            # Fallback: direct worker launch with inline progress
            self._load_games_with_progress(steam_id)

    def _load_games_with_progress(self, user_id: str) -> None:
        if not self.mw.game_service:
            logger.error(t("logs.data_load.game_service_not_initialized"))
            return

        self.mw.tree.set_loading_state(True)

        self.load_worker = GameLoadWorker(self.mw.game_service, user_id)
        self.load_worker.progress_update.connect(self._on_load_progress)
        self.load_worker.finished.connect(self._on_load_finished)
        self.load_worker.start()

    def _on_load_progress(self, step: str, current: int, total: int) -> None:
        if hasattr(self.mw, "loading_label"):
            self.mw.loading_label.setText(step)
            self.mw.loading_label.setVisible(True)
        if hasattr(self.mw, "progress_bar") and total > 0:
            percent = int((current / total) * 100)
            self.mw.progress_bar.setValue(percent)
            self.mw.progress_bar.setVisible(True)

    def _on_load_finished(self, success: bool) -> None:
        if hasattr(self.mw, "loading_label"):
            self.mw.loading_label.setVisible(False)
        if hasattr(self.mw, "progress_bar"):
            self.mw.progress_bar.setVisible(False)

        self.mw.game_manager = self.mw.game_service.game_manager if self.mw.game_service else None

        if not success or not self.mw.game_manager or not self.mw.game_manager.games:
            UIHelper.show_warning(self.mw, t("ui.errors.no_games_found"))
            self.mw.reload_btn.show()
            self.mw.set_status(t("common.error"))
            return

        self.mw.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)
        self.mw.appinfo_manager = self.mw.game_service.appinfo_manager
        from steam_library_manager.services.category_service import CategoryService

        self.mw.category_service = CategoryService(
            localconfig_helper=self.mw.localconfig_helper,
            cloud_parser=self.mw.cloud_storage_parser,
            game_manager=self.mw.game_manager,
        )
        from steam_library_manager.services.metadata_service import MetadataService

        self.mw.metadata_service = MetadataService(
            appinfo_manager=self.mw.appinfo_manager,
            game_manager=self.mw.game_manager,
        )
        from steam_library_manager.services.autocategorize_service import AutoCategorizeService

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
