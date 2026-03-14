#
# steam_library_manager/services/game_service.py
# Service for managing game loading and initialization.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

import requests
from typing import Callable
from pathlib import Path

from steam_library_manager.utils.i18n import t
from steam_library_manager.core.game import Game
from steam_library_manager.core.game_manager import GameManager
from steam_library_manager.core.localconfig_helper import LocalConfigHelper
from steam_library_manager.core.cloud_storage_parser import CloudStorageParser
from steam_library_manager.core.appinfo_manager import AppInfoManager
from steam_library_manager.core.database import Database
from steam_library_manager.core.db.models import DatabaseEntry
from steam_library_manager.core.database_importer import DatabaseImporter
from steam_library_manager.core.packageinfo_parser import PackageInfoParser
from steam_library_manager.utils.license_cache_parser import LicenseCacheParser

logger = logging.getLogger("steamlibmgr.game_service")

__all__ = ["GameService"]


class GameService:
    """Service for managing game loading and initialization."""

    def __init__(self, steam_path: str, api_key: str, cache_dir: str):
        """Initialize with Steam path, API key, and cache directory."""
        self.steam_path = steam_path
        self.api_key = api_key
        self.cache_dir = cache_dir

        self.localconfig_helper: LocalConfigHelper | None = None
        self.cloud_storage_parser: CloudStorageParser | None = None
        self.game_manager: GameManager | None = None
        self.appinfo_manager: AppInfoManager | None = None
        self.database: Database | None = None

    def initialize_parsers(self, localconfig_path: str, user_id: str) -> tuple[bool, bool]:
        """Initialize VDF and Cloud Storage parsers, returns (vdf_ok, cloud_ok)."""
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
        """Open or create the SQLite metadata database."""
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
        """Run the one-time database import from appinfo.vdf."""
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
            if progress_callback:
                progress_callback(msg, current, total)

        logger.info(t("logs.db.import_one_time"))
        importer.import_from_appinfo(_bridge)

    def load_games(self, user_id: str, progress_callback: Callable[[str, int, int], None] | None = None) -> bool:
        """Load all games from API/local, then enrich with DB metadata."""
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
        """Load games and run the full preparation pipeline in one call."""
        # Load games (API + local + DB enrichment)
        success = self.load_games(user_id, progress_callback)
        if not success or not self.game_manager or not self.game_manager.games:
            return False

        # Merge collections from cloud storage
        if progress_callback:
            progress_callback(t("logs.manager.merging"), 0, 0)
        if self.cloud_storage_parser:
            self.game_manager.merge_with_localconfig(self.cloud_storage_parser)

        # Load ONLY custom_metadata.json (skip binary VDF)
        if progress_callback:
            progress_callback(t("logs.service.applying_metadata"), 0, 0)
        if not self.appinfo_manager:
            self.appinfo_manager = AppInfoManager(Path(self.steam_path))
        modifications = self.appinfo_manager.load_modifications_only()

        # Parse packageinfo.vdf + licensecache for ownership data
        if progress_callback:
            progress_callback(t("logs.service.parsing_packages"), 0, 0)
        pkg_parser = PackageInfoParser(Path(self.steam_path))

        # Cross-reference with licensecache for definitive ownership
        from steam_library_manager.config import config as _cfg

        short_id, _ = _cfg.get_detected_user()
        steam32_id = int(short_id) if short_id else None

        if steam32_id:
            license_parser = LicenseCacheParser(Path(self.steam_path), steam32_id)
            owned_packages = license_parser.get_owned_package_ids()

            if owned_packages:
                packageinfo_ids = pkg_parser.get_app_ids_for_packages(owned_packages)
                logger.info(
                    t(
                        "logs.license_cache.cross_reference",
                        packages=len(owned_packages),
                        apps=len(packageinfo_ids),
                    )
                )
            else:
                packageinfo_ids = pkg_parser.get_all_app_ids()
        else:
            packageinfo_ids = pkg_parser.get_all_app_ids()

        # Discover missing games - DB fast path or binary fallback
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

        # Fresh API call to discover newly purchased games
        # (Depressurizer approach - catches games not in local files/DB)
        if progress_callback:
            progress_callback(t("ui.status.api_refresh"), 0, 0)
        new_app_ids = self._refresh_from_api(user_id)
        if new_app_ids:
            if self.cloud_storage_parser:
                self.game_manager.merge_with_localconfig(self.cloud_storage_parser)
            if self.database:
                self._save_new_games_to_db(new_app_ids)

        # Steam Community Profile scrape - DISABLED
        # Profile page uses React CSR; requests.get() only gets a shell.
        # Revisit with session-cookie auth or Playwright.
        # See: TASK_ADDENDUM_FIX_C_REPLACEMENT.md for full analysis.

        # Re-enrich ALL games with DB metadata (fixes fallback names from
        # both discover_missing_games and merge_with_localconfig)
        if self.database:
            self.game_manager.enrich_from_database(self.database)

        # Repair placeholder names ("App XXXXX") from appinfo.vdf
        self._repair_placeholder_names()

        # Apply ONLY custom JSON overrides (not full binary metadata)
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
        """Refresh game list from GetOwnedGames API to catch new purchases."""
        if not self.game_manager:
            return []

        from steam_library_manager.config import config

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
            # Sanitize error message to avoid leaking access token in logs
            if isinstance(e, requests.HTTPError) and e.response is not None:
                safe_msg = f"HTTP {e.response.status_code}"
            else:
                safe_msg = type(e).__name__
            logger.warning("API refresh failed (non-fatal): %s", safe_msg)
            return []

    def _save_new_games_to_db(self, new_app_ids: list[str]) -> None:
        """Persist newly discovered games to the database."""
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

    def _repair_placeholder_names(self) -> None:
        """Replace placeholder names ("App XXXXX") with real names from appinfo.vdf."""
        if not self.game_manager or not self.appinfo_manager:
            return

        from steam_library_manager.core.database import is_placeholder_name

        placeholder_games = [game for game in self.game_manager.games.values() if is_placeholder_name(game.name)]

        if not placeholder_games:
            return

        # Lazy-load appinfo.vdf only if needed
        if not getattr(self.appinfo_manager, "appinfo", None):
            self.appinfo_manager.load_appinfo()

        repaired = 0
        for game in placeholder_games:
            meta = self.appinfo_manager.get_app_metadata(game.app_id)
            real_name = meta.get("name", "")

            if real_name and not is_placeholder_name(real_name):
                game.name = real_name
                if not game.name_overridden:
                    game.sort_name = real_name

                # Also update DB so next startup doesn't repeat the lookup
                if self.database:
                    self.database.update_game_name(int(game.app_id), real_name)

                repaired += 1

        if repaired > 0:
            if self.database:
                self.database.commit()
            logger.info(t("logs.service.placeholder_names_repaired", count=repaired))

    def merge_with_localconfig(self) -> None:
        """Merge collections from active parser into game_manager."""
        if not self.game_manager:
            raise RuntimeError("GameManager not initialized. Call load_games() first.")

        parser = self.cloud_storage_parser  # Only cloud_storage handles categories!

        if not parser:
            raise RuntimeError("No parser available for merging.")

        self.game_manager.merge_with_localconfig(parser)

    def apply_metadata(self) -> None:
        """Apply metadata overrides from appinfo.vdf to loaded games."""
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
        """Return the active cloud storage parser, or None."""
        return self.cloud_storage_parser  # Only cloud_storage handles categories!

    def _refresh_from_profile(self, steam_user_id: str) -> list[str]:
        """Scrape game list from Steam Community profile as a safety net."""
        if not self.game_manager:
            return []

        try:
            from steam_library_manager.integrations.steam_profile_scraper import SteamProfileScraper

            scraper = SteamProfileScraper()
            profile_games = scraper.fetch_games(steam_user_id)

            if not profile_games:
                return []

            new_app_ids: list[str] = []
            for pg in profile_games:
                app_id = str(pg.app_id)
                if app_id not in self.game_manager.games:
                    game = Game(
                        app_id=app_id,
                        name=pg.name,
                        playtime_minutes=pg.playtime_forever,
                        app_type="game",
                    )
                    self.game_manager.games[app_id] = game
                    new_app_ids.append(app_id)

            if new_app_ids:
                logger.info(t("logs.service.profile_discovered", count=len(new_app_ids)))

            return new_app_ids

        except Exception as e:
            logger.warning(t("logs.service.profile_scrape_failed", error=str(e)))
            return []

    def get_load_source_message(self) -> str:
        """Return a message indicating which parser was used to load games."""
        if not self.game_manager:
            return "No games loaded"

        return self.game_manager.get_load_source_message()
