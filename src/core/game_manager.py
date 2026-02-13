# src/core/game_manager.py

"""Core game management logic for the Steam Library Manager.

This module provides the GameManager class, which handles loading games from
multiple sources (Steam API, local files), merging metadata, and fetching
additional details from external APIs.

The Game dataclass lives in src.core.game but is re-exported here for
backwards compatibility.
"""

from __future__ import annotations

import logging
import platform
from pathlib import Path
from typing import Callable

import requests

from src.core.game import (
    Game,
    NON_GAME_APP_IDS,
    NON_GAME_NAME_PATTERNS,
    is_real_game,
)
from src.services.game_detail_service import GameDetailService
from src.services.metadata_enrichment_service import MetadataEnrichmentService
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.game_manager")

__all__ = ["Game", "GameManager"]


class GameManager:
    """Manages loading, merging, and metadata fetching for all games.

    This class is the central hub for game data. It loads games from multiple
    sources (Steam Web API, local files), merges category data from localconfig.vdf,
    applies metadata overrides, and fetches additional details from external APIs.
    """

    # Backwards-compatible class-level references to module constants
    NON_GAME_APP_IDS = NON_GAME_APP_IDS
    NON_GAME_NAME_PATTERNS = NON_GAME_NAME_PATTERNS

    def __init__(self, steam_api_key: str | None, cache_dir: Path, steam_path: Path):
        """Initializes the GameManager.

        Args:
            steam_api_key: Optional Steam Web API key for fetching
                owned games from the Steam API.
            cache_dir: Directory to store JSON cache files for API responses.
            steam_path: Path to the local Steam installation directory.
        """
        self.api_key = steam_api_key
        self.cache_dir = cache_dir
        self.steam_path = steam_path
        self.cache_dir.mkdir(exist_ok=True)

        self.games: dict[str, Game] = {}
        self.steam_user_id: str | None = None
        self.load_source: str = "unknown"
        self.appinfo_manager = None

        # Automatically Enable Proton Filter on Linux
        self.filter_non_games = platform.system() == "Linux"

        # Delegated services (share self.games by reference)
        self.detail_service = GameDetailService(self.games, self.cache_dir)
        self.enrichment_service = MetadataEnrichmentService(self.games, self.cache_dir)

    def load_games(self, steam_user_id: str, progress_callback: Callable[[str, int, int], None] | None = None) -> bool:
        """Main entry point to load games from API and local files.

        This method attempts to load games from both the Steam Web API (if an API key
        is configured) and local Steam files (manifests, appinfo.vdf). It merges the
        results and returns True if at least one source succeeded.

        Args:
            steam_user_id: The SteamID64 of the user whose games to load.
            progress_callback: Optional callback for UI progress updates.
                Receives (message, current, total).

        Returns:
            True if at least one source loaded successfully, False otherwise.
        """
        self.steam_user_id = steam_user_id
        api_success = False

        # STEP 1: Steam Web API (via API key OR OAuth access token)
        from src.config import config as _cfg

        has_credentials = self.api_key or getattr(_cfg, "STEAM_ACCESS_TOKEN", None)
        if has_credentials:
            if progress_callback:
                progress_callback(t("logs.manager.api_trying"), 0, 3)

            logger.info(t("logs.manager.api_trying"))
            api_success = self.load_from_steam_api(steam_user_id)

        # STEP 2: Local Files
        if progress_callback:
            progress_callback(t("logs.manager.local_loading"), 1, 3)

        logger.info(t("logs.manager.local_loading"))
        local_success = self.load_from_local_files(progress_callback)

        # STEP 3: Finalize Status
        if progress_callback:
            progress_callback(t("common.loading"), 2, 3)

        if api_success and local_success:
            self.load_source = "mixed"
        elif api_success:
            self.load_source = "api"
        elif local_success:
            self.load_source = "local"
        else:
            self.load_source = "failed"
            return False

        if progress_callback:
            progress_callback(t("ui.main_window.status_ready"), 3, 3)

        return True

    def load_from_local_files(self, progress_callback: Callable | None = None) -> bool:
        """Loads installed games from local Steam manifests.

        This method uses LocalGamesLoader to scan all Steam library folders
        for appmanifest_*.acf files and extract game information.

        Args:
            progress_callback: Optional callback for progress updates.

        Returns:
            True if games were found, False otherwise.
        """
        # Local import to avoid circular dependency
        from src.core.local_games_loader import LocalGamesLoader

        try:
            loader = LocalGamesLoader(self.steam_path)

            # Load ALL games (installed + from appinfo.vdf)
            games_data = loader.get_all_games()

            if not games_data:
                logger.warning(t("logs.manager.error_local", error="No local games found"))
                return False

            # Load Playtime from localconfig
            from src.config import config

            short_id, _ = config.get_detected_user()
            if short_id:
                localconfig_path = config.get_localconfig_path(short_id)
                playtimes = loader.get_playtime_from_localconfig(localconfig_path)
            else:
                playtimes = {}

            total = len(games_data)
            for i, game_data in enumerate(games_data):
                if progress_callback and i % 50 == 0:
                    # Generic loading message
                    progress_callback(t("common.loading"), i, total)

                app_id = str(game_data["appid"])

                if app_id in self.games:
                    continue

                playtime = playtimes.get(app_id, 0)

                game = Game(app_id=app_id, name=game_data["name"], playtime_minutes=playtime)
                self.games[app_id] = game

            logger.info(t("logs.manager.loaded_local", count=len(games_data)))
            return True

        except (OSError, ValueError, KeyError, RecursionError) as e:
            logger.error(t("logs.manager.error_local", error=e))
            return False

    def load_from_steam_api(self, steam_user_id: str) -> bool:
        """Fetches owned games via the Steam Web API.

        This method calls the Steam Web API's GetOwnedGames endpoint to retrieve
        a list of all games owned by the specified user. It supports both:
        - Traditional API key (stored in self.api_key)
        - OAuth2 access token (from Steam login, passed via environment/global)

        Args:
            steam_user_id: The SteamID64 of the user.

        Returns:
            True if the API call succeeded and games were loaded, False otherwise.
        """
        # Check if we have EITHER an API key OR an access token
        # Access token might be stored globally after login
        from src.config import config

        access_token = getattr(config, "STEAM_ACCESS_TOKEN", None)

        if not self.api_key and not access_token:
            logger.info(t("logs.manager.no_api_key"))
            return False

        try:
            url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"

            # Use access token if available (takes priority over API key)
            if access_token:
                logger.info(t("logs.manager.using_oauth"))
                params = {
                    "access_token": access_token,
                    "steamid": steam_user_id,
                    "include_appinfo": 1,
                    "include_played_free_games": 1,
                    "format": "json",
                }
                response = requests.get(url, params=params, timeout=10)
            else:
                # Traditional API key method
                logger.info(t("logs.manager.using_api_key"))
                params = {
                    "key": self.api_key,
                    "steamid": steam_user_id,
                    "include_appinfo": 1,
                    "include_played_free_games": 1,
                    "format": "json",
                }
                response = requests.get(url, params=params, timeout=10)

            response.raise_for_status()

            data = response.json()

            if "response" not in data or "games" not in data["response"]:
                logger.warning(t("logs.manager.error_api", error="No games in response"))
                return False

            games_data = data["response"]["games"]
            logger.info(t("logs.manager.loaded_api", count=len(games_data)))

            for game_data in games_data:
                app_id = str(game_data["appid"])

                # Use t() for fallback name instead of f-string
                original_name = game_data.get("name") or t("ui.game_details.game_fallback", id=app_id)

                game = Game(app_id=app_id, name=original_name, playtime_minutes=game_data.get("playtime_forever", 0))
                self.games[app_id] = game

            return True

        except (requests.RequestException, ValueError, KeyError) as e:
            # Sanitize error message to avoid leaking API key in logs
            if isinstance(e, requests.HTTPError) and e.response is not None:
                safe_msg = f"HTTP {e.response.status_code}"
            else:
                safe_msg = type(e).__name__
            logger.error(t("logs.manager.error_api", error=safe_msg))
            return False

    def merge_with_localconfig(self, parser) -> None:
        """Merges categories and hidden status from parser into loaded games.

        Delegates to MetadataEnrichmentService.

        Args:
            parser: An instance of CloudStorageParser or LocalConfigHelper.
        """
        self.enrichment_service.merge_with_localconfig(parser)

    def apply_appinfo_data(self, appinfo_data: dict) -> None:
        """Applies last_updated timestamp from appinfo.vdf data.

        Delegates to MetadataEnrichmentService.

        Args:
            appinfo_data: A dictionary of app data from appinfo.vdf.
        """
        self.enrichment_service.apply_appinfo_data(appinfo_data)

    def apply_metadata_overrides(self, appinfo_manager) -> None:
        """Applies metadata overrides from AppInfoManager.

        Delegates to MetadataEnrichmentService.

        Args:
            appinfo_manager: An instance of AppInfoManager with loaded appinfo.vdf data.
        """
        self.appinfo_manager = appinfo_manager
        self.enrichment_service.apply_metadata_overrides(appinfo_manager)

    def get_game(self, app_id: str) -> Game | None:
        """Gets a single game by its app ID.

        Args:
            app_id: The Steam app ID.

        Returns:
            The Game object, or None if not found.
        """
        return self.games.get(app_id)

    def get_games_by_category(self, category: str) -> list[Game]:
        """Gets all games belonging to a specific category.

        Args:
            category: The category name.

        Returns:
            A sorted list of games in this category.
        """
        games = [g for g in self.get_real_games() if g.has_category(category)]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_uncategorized_games(self) -> list[Game]:
        """Gets games that have no user collections (system categories don't count).

        A game is uncategorized if it has NO user-defined collections.
        System categories (Favorites, Hidden) do NOT count as real categories.

        This matches Depressurizer's behavior: A game can be both a Favorite AND Uncategorized,
        or Hidden AND Uncategorized. Only user-created collections remove a game from Uncategorized.

        Returns:
            A sorted list of uncategorized games.
        """
        # System categories that should NOT count as "categorized"
        system_categories = {
            t("ui.categories.favorites"),
            t("ui.categories.hidden")
        }

        uncategorized = []
        for game in self.get_real_games():
            # Filter out system categories
            user_categories = [cat for cat in game.categories if cat not in system_categories]

            # If NO user categories remain → uncategorized!
            if not user_categories:
                uncategorized.append(game)

        return sorted(uncategorized, key=lambda g: g.sort_name.lower())

    def get_favorites(self) -> list[Game]:
        """Gets all favorite games.

        Returns:
            A sorted list of favorite games.
        """
        games = [g for g in self.get_real_games() if g.is_favorite()]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_all_categories(self) -> dict[str, int]:
        """Gets all categories and their game counts.

        Returns:
            A dictionary mapping category names to game counts.
        """
        categories = {}
        for game in self.get_real_games():
            for category in game.categories:
                categories[category] = categories.get(category, 0) + 1
        return categories

    def fetch_game_details(self, app_id: str) -> bool:
        """Fetches additional details for a game from external APIs.

        Delegates to GameDetailService.

        Args:
            app_id: The Steam app ID.

        Returns:
            True if the game exists, False otherwise.
        """
        return self.detail_service.fetch_game_details(app_id)

    def get_load_source_message(self) -> str:
        """Returns a localized status message about the load source.

        Returns:
            A localized message indicating how games were loaded (API, local, or mixed).
        """
        if self.load_source == "api":
            return t("logs.manager.loaded_api", count=len(self.games))
        elif self.load_source == "local":
            return t("logs.manager.loaded_local", count=len(self.games))
        elif self.load_source == "mixed":
            return t("logs.manager.loaded_mixed", count=len(self.games))
        else:
            return t("ui.main_window.status_ready")

    @staticmethod
    def is_real_game(game: Game) -> bool:
        """Checks if a game is a real game (not Proton/Steam runtime).

        Delegates to the module-level is_real_game() function in src.core.game.

        Args:
            game: The game to check.

        Returns:
            True if real game, False if tool/runtime.
        """
        return is_real_game(game)

    def get_real_games(self) -> list[Game]:
        """Returns only real games (excludes Proton/Steam runtime tools).

        On Linux, Proton and Steam Runtime are automatically filtered.
        On Windows, all games are returned.

        Returns:
            List of real games.
        """
        if self.filter_non_games:
            return [g for g in self.games.values() if is_real_game(g)]
        else:
            return list(self.games.values())

    def get_all_games(self) -> list[Game]:
        """Returns ALL games (including tools).

        This method always returns all games, regardless of the filter.
        For most purposes, use get_real_games() instead!

        Returns:
            List of all games.
        """
        return list(self.games.values())

    def get_game_statistics(self) -> dict[str, int]:
        """Returns game statistics (for development/debugging).

        Returns:
            dict containing:
            - total_games: Number of real games (excluding Proton/tools)
            - games_in_categories: Number of unique games in categories
            - category_count: Number of categories (excluding "All Games")
            - uncategorized_games: Number of games without categories
        """
        # Real games (without Proton on Linux)
        real_games = self.get_real_games()

        # Unique games in collections (each game only 1x)
        games_in_categories = set()
        for game in real_games:
            if game.categories:
                games_in_categories.add(game.app_id)

        # Number of collections (excluding "All Games")
        all_categories = self.get_all_categories()
        category_count = len(all_categories)

        # Uncategorized Games
        uncategorized = len(real_games) - len(games_in_categories)

        return {
            "total_games": len(real_games),
            "games_in_categories": len(games_in_categories),
            "category_count": category_count,
            "uncategorized_games": uncategorized,
        }
