"""
Handler for data loading operations.

This module contains the DataLoadHandler that manages the initial data
loading sequence including Steam path detection, parser initialization,
and game loading with progress tracking.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QProgressDialog
from PyQt6.QtCore import Qt

from src.config import config
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t
from src.integrations.steam_store import SteamStoreScraper
from src.ui.workers import GameLoadWorker

import logging

logger = logging.getLogger("steamlibmgr.data_load_handler")

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class DataLoadHandler:
    """Handler for all data loading operations.

    Manages the complete data loading workflow:
    - Steam path detection
    - User detection
    - Parser initialization
    - Game loading with progress
    - Service initialization

    Attributes:
        mw: Reference to the MainWindow instance.
        progress_dialog: Progress dialog shown during loading.
        load_worker: Worker thread for async game loading.
    """

    def __init__(self, main_window: "MainWindow"):
        """Initialize the data load handler.

        Args:
            main_window: The MainWindow instance.
        """
        self.mw = main_window
        self.progress_dialog: QProgressDialog | None = None
        self.load_worker: GameLoadWorker | None = None

    def load_data(self) -> None:
        """Perform the initial data loading sequence.

        Detects Steam path and user, initializes parsers and managers,
        and starts the game loading process.
        """
        self.mw.set_status(t("common.loading"))

        if not config.STEAM_PATH:
            UIHelper.show_warning(self.mw, t("logs.main.steam_not_found"))
            self.mw.reload_btn.show()
            return

        short_id, long_id = config.get_detected_user()
        target_id = config.STEAM_USER_ID if config.STEAM_USER_ID else long_id

        if not short_id and not target_id:
            UIHelper.show_warning(self.mw, t("ui.errors.no_users_found"))
            self.mw.reload_btn.show()
            return

        # Restore login state if STEAM_USER_ID was saved
        if config.STEAM_USER_ID and not self.mw.steam_username:
            self.mw.steam_username = DataLoadHandler.fetch_steam_persona_name(config.STEAM_USER_ID)
            self.mw.refresh_toolbar()

        display_id = self.mw.steam_username if self.mw.steam_username else (target_id if target_id else short_id)
        self.mw.user_label.setText(t("ui.main_window.user_label", user_id=display_id))

        # Initialize GameService
        from src.services.game_service import GameService

        self.mw.game_service = GameService(str(config.STEAM_PATH), config.STEAM_API_KEY, str(config.CACHE_DIR))

        # Initialize parsers through GameService
        config_path = config.get_localconfig_path(short_id)
        if not config_path:
            UIHelper.show_error(self.mw, t("ui.errors.localconfig_load_error"))
            self.mw.reload_btn.show()
            return

        vdf_success, cloud_success = self.mw.game_service.initialize_parsers(str(config_path), short_id)

        if not vdf_success and not cloud_success:
            UIHelper.show_error(self.mw, t("ui.errors.localconfig_load_error"))
            self.mw.reload_btn.show()
            return

        # Set references for backward compatibility
        self.mw.localconfig_helper = self.mw.game_service.localconfig_helper
        self.mw.cloud_storage_parser = self.mw.game_service.cloud_storage_parser

        # Load games through GameService
        self.load_games_with_progress(target_id)

    def load_games_with_progress(self, user_id: str | None) -> None:
        """Start game loading with a progress dialog.

        Args:
            user_id: The Steam user ID to load games for, or None for local only.
        """
        self.progress_dialog = QProgressDialog(t("common.loading"), t("common.cancel"), 0, 100, self.mw)
        self.progress_dialog.setWindowTitle(t("ui.main_window.status_ready"))
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)

        self.load_worker = GameLoadWorker(self.mw.game_service, user_id or "local")
        # noinspection PyUnresolvedReferences
        self.load_worker.progress_update.connect(self.on_load_progress)
        # noinspection PyUnresolvedReferences
        self.load_worker.finished.connect(self.on_load_finished)
        self.load_worker.start()

    def load_games_with_steam_login(self, steam_id: str, session_or_token) -> None:
        """Load games after Steam login with access token or session.

        This method is called after successful Steam authentication to reload
        the game library with Steam Web API access.

        Args:
            steam_id: The Steam ID64 of the authenticated user
            session_or_token: Either a requests.Session or access_token string
        """
        logger.info(t("logs.auth.loading_games_after_login"))

        # Store session/token for API access
        if isinstance(session_or_token, str):
            logger.info(t("logs.auth.auth_mode_token"))
        else:
            logger.info(t("logs.auth.auth_mode_session"))

        # Simply reload games with the user_id
        # The GameLoadWorker will use the session/token if available
        self.load_games_with_progress(steam_id)

    def on_load_progress(self, step: str, current: int, total: int) -> None:
        """Update the progress dialog during game loading.

        Args:
            step: Description of the current loading step.
            current: Current progress count.
            total: Total items to process.
        """
        if self.progress_dialog:
            self.progress_dialog.setLabelText(step)
            if total > 0:
                percent = int((current / total) * 100)
                self.progress_dialog.setValue(percent)

    def on_load_finished(self, success: bool) -> None:
        """Handle completion of the game loading process.

        Args:
            success: Whether loading completed successfully.
        """
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        # Get game_manager reference from game_service
        self.mw.game_manager = self.mw.game_service.game_manager if self.mw.game_service else None

        if not success or not self.mw.game_manager or not self.mw.game_manager.games:
            UIHelper.show_warning(self.mw, t("ui.errors.no_games_found"))
            self.mw.reload_btn.show()
            self.mw.set_status(t("common.error"))
            return

        # Merge collections using GameService
        self.mw.game_service.merge_with_localconfig()

        # Apply metadata using GameService
        self.mw.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)
        self.mw.game_service.apply_metadata()

        # Set appinfo_manager reference for backward compatibility
        self.mw.appinfo_manager = self.mw.game_service.appinfo_manager

        # Initialize CategoryService after parsers and game_manager are ready
        from src.services.category_service import CategoryService

        self.mw.category_service = CategoryService(
            localconfig_helper=self.mw.localconfig_helper,
            cloud_parser=self.mw.cloud_storage_parser,
            game_manager=self.mw.game_manager,
        )

        # Initialize MetadataService after appinfo_manager is ready
        from src.services.metadata_service import MetadataService

        self.mw.metadata_service = MetadataService(
            appinfo_manager=self.mw.appinfo_manager, game_manager=self.mw.game_manager
        )

        # Initialize AutoCategorizeService after category_service is ready
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

        # Update statistics
        self.mw.update_statistics()

    @staticmethod
    def fetch_steam_persona_name(steam_id: str) -> str:
        """Fetches the public persona name from Steam Community XML.

        Args:
            steam_id: The Steam ID64 to look up.

        Returns:
            The persona name if found, otherwise the original steam_id.
        """
        import requests

        # noinspection PyPep8Naming
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

        return steam_id
