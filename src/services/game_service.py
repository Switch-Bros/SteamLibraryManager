"""Service for managing game loading and initialization.

This module provides the GameService class which handles loading games from Steam API,
initializing parsers, and managing game data.
"""
from __future__ import annotations

import logging

from typing import Callable
from pathlib import Path

from src.utils.i18n import t
from src.core.game_manager import GameManager
from src.core.localconfig_helper import LocalConfigHelper
from src.core.cloud_storage_parser import CloudStorageParser
from src.core.appinfo_manager import AppInfoManager

logger = logging.getLogger("steamlibmgr.game_service")

__all__ = ['GameService']

class GameService:
    """Service for managing game loading and initialization.

    Handles loading games from Steam API, initializing VDF and Cloud Storage parsers,
    and managing game data through GameManager.

    Attributes:
        steam_path: Path to Steam installation directory.
        api_key: Steam API key for fetching game data.
        cache_dir: Directory for caching game data.
        localconfig_helper: Helper for Steam's localconfig.vdf (hidden status only).
        cloud_storage_parser: Parser for Steam's cloud storage JSON files.
        game_manager: Manager for game data.
        appinfo_manager: Manager for appinfo.vdf metadata.
    """

    def __init__(self, steam_path: str, api_key: str, cache_dir: str):
        """Initializes the GameService.

        Args:
            steam_path: Path to Steam installation directory.
            api_key: Steam API key for fetching game data.
            cache_dir: Directory for caching game data.
        """
        self.steam_path = steam_path
        self.api_key = api_key
        self.cache_dir = cache_dir

        self.localconfig_helper: LocalConfigHelper | None = None
        self.cloud_storage_parser: CloudStorageParser | None = None
        self.game_manager: GameManager | None = None
        self.appinfo_manager: AppInfoManager | None = None

    def initialize_parsers(self, localconfig_path: str, user_id: str) -> tuple[bool, bool]:
        """Initializes VDF and Cloud Storage parsers.

        Args:
            localconfig_path: Path to localconfig.vdf file.
            user_id: Steam user ID (short format, e.g., "12345678").

        Returns:
            Tuple of (vdf_success, cloud_success) indicating which parsers initialized successfully.
        """
        vdf_success = False
        cloud_success = False

        # Try VDF parser
        try:
            self.localconfig_helper = LocalConfigHelper(localconfig_path)
            if self.localconfig_helper.load():
                vdf_success = True
            else:
                self.localconfig_helper = None
                vdf_success = False
        except (OSError, FileNotFoundError, ValueError) as e:
            logger.error(t('logs.service.localconfig_init_error', error=e))
            self.localconfig_helper = None

        # Try Cloud Storage parser
        try:
            self.cloud_storage_parser = CloudStorageParser(self.steam_path, user_id)
            if self.cloud_storage_parser.load():
                cloud_success = True
            else:
                self.cloud_storage_parser = None
        except Exception as e:
            logger.error(t('logs.service.cloud_parser_init_error', error=e))
            self.cloud_storage_parser = None

        return vdf_success, cloud_success

    def load_games(self, user_id: str, progress_callback: Callable[[str, int, int], None] | None = None) -> bool:
        """Loads all games from Steam API and local files.

        Args:
            user_id: Steam user ID (long format, e.g., "76561197960287930") to load games for.
            progress_callback: Optional callback for progress updates (step, current, total).

        Returns:
            True if games were loaded successfully and at least one game was found.

        Raises:
            RuntimeError: If parsers are not initialized.
        """
        if not self.cloud_storage_parser:  # localconfig is not a category parser!
            raise RuntimeError("Parsers not initialized. Call initialize_parsers() first.")

        # Initialize GameManager with Path objects
        self.game_manager = GameManager(
            self.api_key,
            Path(self.cache_dir),
            Path(self.steam_path)
        )

        # Load games
        success = self.game_manager.load_games(user_id, progress_callback)

        return success and bool(self.game_manager.games)

    def merge_with_localconfig(self) -> None:
        """Merges collections from active parser into game_manager.

        Uses cloud storage parser if available, otherwise falls back to VDF parser.

        Raises:
            RuntimeError: If no parser or game_manager is available.
        """
        if not self.game_manager:
            raise RuntimeError("GameManager not initialized. Call load_games() first.")

        parser = self.cloud_storage_parser  # Only cloud_storage handles categories!

        if not parser:
            raise RuntimeError("No parser available for merging.")

        self.game_manager.merge_with_localconfig(parser)

    def apply_metadata(self) -> None:
        """Applies metadata overrides from appinfo.vdf to loaded games.

        Raises:
            RuntimeError: If game_manager is not initialized.
        """
        if not self.game_manager:
            raise RuntimeError("GameManager not initialized. Call load_games() first.")

        # Initialize AppInfoManager if not already done
        if not self.appinfo_manager:
            self.appinfo_manager = AppInfoManager(Path(self.steam_path))
            self.appinfo_manager.load_appinfo()

        self.game_manager.apply_metadata_overrides(self.appinfo_manager)

    def get_active_parser(self) -> CloudStorageParser | None:
        """Returns the active parser (cloud storage only).

        Returns:
            CloudStorageParser instance, or None if not initialized.
        """
        return self.cloud_storage_parser  # Only cloud_storage handles categories!

    def get_load_source_message(self) -> str:
        """Returns a message indicating which parser was used to load games.

        Returns:
            Human-readable message about the load source.
        """
        if not self.game_manager:
            return "No games loaded"

        return self.game_manager.get_load_source_message()