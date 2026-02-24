"""Service for managing game loading and initialization.

This module provides the GameService class which handles loading games from Steam API,
initializing parsers, and managing game data.
"""

from __future__ import annotations

import logging

import requests
from typing import Callable
from pathlib import Path

from src.utils.i18n import t
from src.core.game import Game
from src.core.game_manager import GameManager
from src.core.localconfig_helper import LocalConfigHelper
from src.core.cloud_storage_parser import CloudStorageParser
from src.core.appinfo_manager import AppInfoManager
from src.core.database import Database
from src.core.db.models import DatabaseEntry
from src.core.database_importer import DatabaseImporter
from src.core.packageinfo_parser import PackageInfoParser

logger = logging.getLogger("steamlibmgr.game_service")

__all__ = ["GameService"]


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
        self.database: Database | None = None

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
            logger.error(t("logs.service.localconfig_init_error", error=e))
            self.localconfig_helper = None

        # Try Cloud Storage parser
        try:
            self.cloud_storage_parser = CloudStorageParser(self.steam_path, user_id)
            if self.cloud_storage_parser.load():
                cloud_success = True
            else:
                self.cloud_storage_parser = None
        except Exception as e:
            logger.error(t("logs.service.cloud_parser_init_error", error=e))
            self.cloud_storage_parser = None

        return vdf_success, cloud_success

    def _init_database(self) -> Database | None:
        """Initialize the metadata database.

        Opens (or creates) the SQLite database under the app's data directory.
        On first run the database will be empty and needs an import.

        Returns:
            Database instance, or None on failure.
        """
        db_dir = Path(self.cache_dir).parent  # data/ directory
        db_path = db_dir / "metadata.db"

        try:
            db = Database(db_path)
            logger.info(t("logs.db.initializing"))
            return db
        except Exception as e:
            logger.error(t("logs.db.schema_error", error=str(e)))
            return None

    def _run_initial_import(
        self,
        db: Database,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> None:
        """Run the one-time database import from appinfo.vdf.

        Args:
            db: Database instance.
            progress_callback: Optional progress callback.
        """
        # Quick check BEFORE loading appinfo.vdf (avoids ~30s parse on every start)
        if db.get_game_count() > 0:
            logger.info(t("logs.db.already_initialized"))
            return

        # DB is empty — load appinfo.vdf for one-time import
        if not self.appinfo_manager:
            self.appinfo_manager = AppInfoManager(Path(self.steam_path))
            self.appinfo_manager.load_appinfo()

        importer = DatabaseImporter(db, self.appinfo_manager)

        def _bridge(current: int, total: int, msg: str) -> None:
            """Bridge 3-arg importer callback to GameService callback."""
            if progress_callback:
                progress_callback(msg, current, total)

        logger.info(t("logs.db.import_one_time"))
        importer.import_from_appinfo(_bridge)

    def load_games(self, user_id: str, progress_callback: Callable[[str, int, int], None] | None = None) -> bool:
        """Loads all games from API/local, then enriches with DB metadata.

        Flow:
            1. Initialize database (create/open)
            2. If DB empty: import from appinfo.vdf (one-time, ~30s)
            3. Load games from API + local files (authoritative names/playtime)
            4. Enrich loaded games with DB metadata (developer, publisher, genres)

        Args:
            user_id: Steam user ID (long format, e.g., "76561197960287930") to load games for.
            progress_callback: Optional callback for progress updates (step, current, total).

        Returns:
            True if games were loaded successfully and at least one game was found.

        Raises:
            RuntimeError: If parsers are not initialized.
        """
        if not self.cloud_storage_parser:
            raise RuntimeError("Parsers not initialized. Call initialize_parsers() first.")

        # Initialize GameManager with Path objects
        self.game_manager = GameManager(self.api_key, Path(self.cache_dir), Path(self.steam_path))

        # Initialize database (but don't load from it yet)
        self.database = self._init_database()

        if self.database:
            # Run initial import if DB is empty
            self._run_initial_import(self.database, progress_callback)
            # Clean up any leftover placeholder names from previous imports
            self.database.repair_placeholder_names()

        # Load games from API/local FIRST (these have authoritative names)
        success = self.game_manager.load_games(user_id, progress_callback)

        # THEN enrich with cached metadata from DB (developer, publisher, genres etc.)
        if self.database and self.game_manager.games:
            self.game_manager.enrich_from_database(self.database)

        return success and bool(self.game_manager.games)

    def load_and_prepare(self, user_id: str, progress_callback: Callable[[str, int, int], None] | None = None) -> bool:
        """Loads games and runs the full preparation pipeline in one call.

        Designed to run entirely in a worker thread so the UI stays responsive.
        Uses lazy-load: the expensive binary appinfo.vdf is NOT parsed at
        startup.  Instead the SQLite DB provides type/name data for discovery,
        and only the lightweight custom_metadata.json is loaded for overrides.

        Pipeline:
            1. load_games() — API + local + DB enrichment
            2. merge_with_localconfig() — assign collections
            3. appinfo_manager.load_modifications_only() — JSON only (~5ms)
            4. PackageInfoParser.get_all_app_ids() — package IDs
            5. database.get_app_type_lookup() -> discover_missing_games(db_type_lookup=...)
            6. apply_custom_overrides(modifications) — JSON overrides only

        Fallback: if no DB exists (should not happen after Phase 1.2) the
        legacy binary path is used.

        Args:
            user_id: Steam user ID (long format) to load games for.
            progress_callback: Optional callback for progress updates (step, current, total).

        Returns:
            True if games were loaded successfully and at least one game was found.

        Raises:
            RuntimeError: If parsers are not initialized.
        """
        # Step 1: Load games (API + local + DB enrichment)
        success = self.load_games(user_id, progress_callback)
        if not success or not self.game_manager or not self.game_manager.games:
            return False

        # Step 2: Merge collections from cloud storage
        if progress_callback:
            progress_callback(t("logs.manager.merging"), 0, 0)
        if self.cloud_storage_parser:
            self.game_manager.merge_with_localconfig(self.cloud_storage_parser)

        # Step 3: Load ONLY custom_metadata.json (skip binary VDF)
        if progress_callback:
            progress_callback(t("logs.service.applying_metadata"), 0, 0)
        if not self.appinfo_manager:
            self.appinfo_manager = AppInfoManager(Path(self.steam_path))
        modifications = self.appinfo_manager.load_modifications_only()

        # Step 4: Parse packageinfo.vdf for ownership data
        if progress_callback:
            progress_callback(t("logs.service.parsing_packages"), 0, 0)
        pkg_parser = PackageInfoParser(Path(self.steam_path))
        packageinfo_ids = pkg_parser.get_all_app_ids()

        # Step 5: Discover missing games — DB fast path or binary fallback
        if progress_callback:
            progress_callback(t("logs.service.discovering_games"), 0, 0)

        db_type_lookup: dict[str, tuple[str, str]] | None = None
        if self.database and self.database.get_game_count() > 0:
            db_type_lookup = self.database.get_app_type_lookup()

        if db_type_lookup is not None:
            # Fast path: use DB for type/name resolution
            discovered = self.game_manager.discover_missing_games(
                self.localconfig_helper,
                self.appinfo_manager,
                packageinfo_ids,
                db_type_lookup=db_type_lookup,
            )
        else:
            # Fallback: load binary (first run or missing DB)
            self.appinfo_manager.load_appinfo()
            discovered = self.game_manager.discover_missing_games(
                self.localconfig_helper,
                self.appinfo_manager,
                packageinfo_ids,
            )

        # Re-merge categories for newly discovered games
        if discovered > 0 and self.cloud_storage_parser:
            self.game_manager.merge_with_localconfig(self.cloud_storage_parser)

        # Step 5.5: Fresh API call to discover newly purchased games
        # (Depressurizer approach — catches games not in local files/DB)
        if progress_callback:
            progress_callback(t("ui.status.api_refresh"), 0, 0)
        new_app_ids = self._refresh_from_api(user_id)
        if new_app_ids:
            if self.cloud_storage_parser:
                self.game_manager.merge_with_localconfig(self.cloud_storage_parser)
            if self.database:
                self._save_new_games_to_db(new_app_ids)

        # Re-enrich ALL games with DB metadata (fixes fallback names from
        # both discover_missing_games and merge_with_localconfig)
        if self.database:
            self.game_manager.enrich_from_database(self.database)

        # Step 6: Apply ONLY custom JSON overrides (not full binary metadata)
        if progress_callback:
            progress_callback(t("logs.service.applying_overrides"), 0, 0)
        if db_type_lookup is not None:
            # Lazy path: only custom overrides from JSON
            self.game_manager.apply_custom_overrides(modifications)
        else:
            # Fallback: full binary metadata overrides
            self.game_manager.apply_metadata_overrides(self.appinfo_manager)

        return True

    def _refresh_from_api(self, steam_user_id: str) -> list[str]:
        """Refresh game list from GetOwnedGames API to catch new purchases.

        Runs AFTER the main loading pipeline as a safety net to discover games
        purchased since the last Steam Client sync. This is the Depressurizer
        approach: always do a fresh API call.

        Args:
            steam_user_id: SteamID64 of the user.

        Returns:
            List of newly discovered app_ids (empty if none found or on error).
        """
        if not self.game_manager:
            return []

        from src.config import config

        access_token = getattr(config, "STEAM_ACCESS_TOKEN", None)

        if not access_token and not self.api_key:
            logger.debug("No API credentials — skipping refresh")
            return []

        try:
            url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"

            if access_token:
                params = {
                    "access_token": access_token,
                    "steamid": steam_user_id,
                    "include_appinfo": 1,
                    "include_played_free_games": 1,
                    "include_free_sub": 1,
                    "skip_unvetted_apps": 0,
                    "format": "json",
                }
            else:
                params = {
                    "key": self.api_key,
                    "steamid": steam_user_id,
                    "include_appinfo": 1,
                    "include_played_free_games": 1,
                    "include_free_sub": 1,
                    "skip_unvetted_apps": 0,
                    "format": "json",
                }

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            games_data = data.get("response", {}).get("games", [])
            if not games_data:
                return []

            new_app_ids: list[str] = []

            for game_data in games_data:
                app_id = str(game_data["appid"])

                if app_id not in self.game_manager.games:
                    name = game_data.get("name") or t("ui.game_details.game_fallback", id=app_id)
                    playtime = game_data.get("playtime_forever", 0)

                    game = Game(
                        app_id=app_id,
                        name=name,
                        playtime_minutes=playtime,
                        app_type="game",
                    )
                    self.game_manager.games[app_id] = game
                    new_app_ids.append(app_id)
                    logger.debug("API refresh: discovered %s (%s)", app_id, name)

            if new_app_ids:
                logger.info("API refresh: discovered %d new games", len(new_app_ids))

            return new_app_ids

        except Exception as e:
            logger.warning("API refresh failed (non-fatal): %s", e)
            return []

    def _save_new_games_to_db(self, new_app_ids: list[str]) -> None:
        """Persist newly discovered games to the database.

        Args:
            new_app_ids: App IDs of games to save.
        """
        if not self.database or not self.game_manager:
            return

        for app_id in new_app_ids:
            game = self.game_manager.games.get(app_id)
            if not game:
                continue
            entry = DatabaseEntry(
                app_id=int(app_id),
                name=game.name,
                app_type=game.app_type or "game",
            )
            try:
                self.database.insert_game(entry)
            except Exception as e:
                logger.debug("DB insert for %s failed: %s", app_id, e)

        self.database.commit()

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

        # Parse packageinfo.vdf for definitive ownership data
        pkg_parser = PackageInfoParser(Path(self.steam_path))
        packageinfo_ids = pkg_parser.get_all_app_ids()

        # Discover games missing from API using multiple local sources
        if self.appinfo_manager:
            discovered = self.game_manager.discover_missing_games(
                self.localconfig_helper, self.appinfo_manager, packageinfo_ids
            )
            # Re-merge categories for newly discovered games
            if discovered > 0 and self.cloud_storage_parser:
                self.game_manager.merge_with_localconfig(self.cloud_storage_parser)

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
