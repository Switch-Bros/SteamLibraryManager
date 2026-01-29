# src/core/game_manager.py

"""
Core game management logic for the Steam Library Manager.

This module provides the Game dataclass and GameManager class, which handle
loading games from multiple sources (Steam API, local files), merging metadata,
and fetching additional details from external APIs.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

from src.utils.i18n import t


@dataclass
class Game:
    """
    Represents a single Steam game with all its metadata.

    This dataclass stores all information about a game, including basic info
    (name, app_id), playtime, categories, metadata (developer, publisher),
    and extended data from external APIs (ProtonDB, Steam Deck, reviews).
    """
    app_id: str
    name: str
    playtime_minutes: int = 0
    last_played: Optional[datetime] = None
    categories: List[str] = None

    # Hidden Status (localconfig)
    hidden: bool = False

    # Metadata
    developer: str = ""
    publisher: str = ""
    release_year: str = ""
    genres: List[str] = None
    tags: List[str] = None

    # Sorting
    sort_name: str = ""

    # Override flags
    name_overridden: bool = False

    # Extended data
    proton_db_rating: str = ""
    steam_deck_status: str = ""
    review_score: str = ""
    review_count: int = 0
    last_updated: str = ""
    steam_grid_db_url: str = ""

    # Legacy / UI Compatibility
    proton_db_tier: str = ""
    steam_review_score: int = 0
    steam_review_desc: str = ""
    steam_review_total: str = ""

    # Images
    icon_url: str = ""
    cover_url: str = ""

    def __post_init__(self):
        """Initializes default lists and sort name if missing."""
        if self.categories is None: self.categories = []
        if self.genres is None: self.genres = []
        if self.tags is None: self.tags = []

        if not self.sort_name:
            self.sort_name = self.name

    @property
    def playtime_hours(self) -> float:
        """
        Returns playtime in hours, rounded to 1 decimal place.

        Returns:
            float: Playtime in hours.
        """
        return round(self.playtime_minutes / 60, 1)

    def has_category(self, category: str) -> bool:
        """
        Checks if the game belongs to a specific category.

        Args:
            category (str): The category name to check.

        Returns:
            bool: True if the game has this category, False otherwise.
        """
        return category in self.categories

    def is_favorite(self) -> bool:
        """
        Checks if the game is marked as a favorite.

        Returns:
            bool: True if 'favorite' is in the game's categories, False otherwise.
        """
        return 'favorite' in self.categories


class GameManager:
    """
    Manages loading, merging, and metadata fetching for all games.

    This class is the central hub for game data. It loads games from multiple
    sources (Steam Web API, local files), merges category data from localconfig.vdf,
    applies metadata overrides, and fetches additional details from external APIs.
    """

    def __init__(self, steam_api_key: Optional[str], cache_dir: Path, steam_path: Path):
        """
        Initializes the GameManager.

        Args:
            steam_api_key (Optional[str]): Optional Steam Web API key for fetching
                                           owned games from the Steam API.
            cache_dir (Path): Directory to store JSON cache files for API responses.
            steam_path (Path): Path to the local Steam installation directory.
        """
        self.api_key = steam_api_key
        self.cache_dir = cache_dir
        self.steam_path = steam_path
        self.cache_dir.mkdir(exist_ok=True)

        self.games: Dict[str, Game] = {}
        self.steam_user_id: Optional[str] = None
        self.load_source: str = "unknown"
        self.appinfo_manager = None

    def load_games(self, steam_user_id: str,
                   progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        Main entry point to load games from API and local files.

        This method attempts to load games from both the Steam Web API (if an API key
        is configured) and local Steam files (manifests, appinfo.vdf). It merges the
        results and returns True if at least one source succeeded.

        Args:
            steam_user_id (str): The SteamID64 of the user whose games to load.
            progress_callback (Optional[Callable[[str, int, int], None]]): Optional callback
                                                                           for UI progress updates.
                                                                           Receives (message, current, total).

        Returns:
            bool: True if at least one source loaded successfully, False otherwise.
        """
        self.steam_user_id = steam_user_id
        api_success = False

        # STEP 1: Steam Web API
        if self.api_key:
            if progress_callback:
                progress_callback(t('logs.manager.api_trying'), 0, 3)

            print(t('logs.manager.api_trying'))
            api_success = self.load_from_steam_api(steam_user_id)

        # STEP 2: Local Files
        if progress_callback:
            progress_callback(t('logs.manager.local_loading'), 1, 3)

        print(t('logs.manager.local_loading'))
        local_success = self.load_from_local_files(progress_callback)

        # STEP 3: Finalize Status
        if progress_callback:
            progress_callback(t('common.loading'), 2, 3)

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
            progress_callback(t('ui.main_window.status_ready'), 3, 3)

        return True

    def load_from_local_files(self, progress_callback: Optional[Callable] = None) -> bool:
        """
        Loads installed games from local Steam manifests.

        This method uses LocalGamesLoader to scan all Steam library folders
        for appmanifest_*.acf files and extract game information.

        Args:
            progress_callback (Optional[Callable]): Optional callback for progress updates.

        Returns:
            bool: True if games were found, False otherwise.
        """
        # Local import to avoid circular dependency
        from src.core.local_games_loader import LocalGamesLoader

        try:
            loader = LocalGamesLoader(self.steam_path)

            # Load ALL games (installed + from appinfo.vdf)
            games_data = loader.get_all_games()

            if not games_data:
                print(t('logs.manager.error_local', error="No local games found"))
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
                    progress_callback(t('common.loading'), i, total)

                app_id = str(game_data['appid'])

                if app_id in self.games:
                    continue

                playtime = playtimes.get(app_id, 0)

                game = Game(
                    app_id=app_id,
                    name=game_data['name'],
                    playtime_minutes=playtime
                )
                self.games[app_id] = game

            print(t('logs.manager.loaded_local', count=len(games_data)))
            return True

        except (OSError, ValueError, KeyError, RecursionError) as e:
            print(t('logs.manager.error_local', error=e))
            return False

    def load_from_steam_api(self, steam_user_id: str) -> bool:
        """
        Fetches owned games via the Steam Web API.

        This method calls the Steam Web API's GetOwnedGames endpoint to retrieve
        a list of all games owned by the specified user.

        Args:
            steam_user_id (str): The SteamID64 of the user.

        Returns:
            bool: True if the API call succeeded and games were loaded, False otherwise.
        """
        if not self.api_key:
            print("Info: No API Key configured.")
            return False

        try:
            url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
            params = {
                'key': self.api_key,
                'steamid': steam_user_id,
                'include_appinfo': 1,
                'include_played_free_games': 1,
                'format': 'json'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'response' not in data or 'games' not in data['response']:
                print(t('logs.manager.error_api', error="No games in response"))
                return False

            games_data = data['response']['games']
            print(t('logs.manager.loaded_api', count=len(games_data)))

            for game_data in games_data:
                app_id = str(game_data['appid'])

                # Use t() for fallback name instead of f-string
                original_name = game_data.get('name') or t('common.game_fallback', id=app_id)

                game = Game(
                    app_id=app_id,
                    name=original_name,
                    playtime_minutes=game_data.get('playtime_forever', 0)
                )
                self.games[app_id] = game

            return True

        except (requests.RequestException, ValueError, KeyError) as e:
            print(t('logs.manager.error_api', error=e))
            return False

    def merge_with_localconfig(self, parser) -> None:
        """
        Merges categories and hidden status from localconfig.vdf into loaded games.

        This method takes a LocalConfigParser instance and applies category
        assignments and hidden status to the games in memory. It also adds
        games that exist in localconfig but weren't loaded from other sources.

        Args:
            parser: An instance of LocalConfigParser with loaded localconfig.vdf data.
        """
        print(t('logs.manager.merging'))
        local_app_ids = set(parser.get_all_app_ids())

        # List of hidden apps
        hidden_apps = set(parser.get_hidden_apps())

        for app_id in self.games:
            # Set hidden status
            if app_id in hidden_apps:
                self.games[app_id].hidden = True

            if app_id in local_app_ids:
                categories = parser.get_app_categories(app_id)
                self.games[app_id].categories = categories

        api_app_ids = set(self.games.keys())
        missing_ids = local_app_ids - api_app_ids

        if missing_ids:
            # Add games found in localconfig but not in API/Manifests
            for app_id in missing_ids:
                # Use t() for fallback name
                name = self._get_cached_name(app_id) or t('common.game_fallback', id=app_id)

                game = Game(app_id=app_id, name=name)
                game.categories = parser.get_app_categories(app_id)

                if app_id in hidden_apps:
                    game.hidden = True

                self.games[app_id] = game

    def _get_cached_name(self, app_id: str) -> Optional[str]:
        """
        Tries to retrieve a game name from the local JSON cache.

        Args:
            app_id (str): The app ID to look up.

        Returns:
            Optional[str]: The cached game name, or None if not found.
        """
        cache_file = self.cache_dir / 'store_data' / f'{app_id}.json'
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    return data.get('name')
            except (OSError, json.JSONDecodeError):
                pass
        return None

    def apply_appinfo_data(self, appinfo_data: Dict) -> None:
        """
        Applies last_updated timestamp from appinfo.vdf data.

        Args:
            appinfo_data (Dict): A dictionary of app data from appinfo.vdf.
        """
        for app_id, data in appinfo_data.items():
            if app_id in self.games:
                if 'common' in data and 'last_updated' in data['common']:
                    ts = data['common']['last_updated']
                    try:
                        dt = datetime.fromtimestamp(int(ts))
                        self.games[app_id].last_updated = dt.strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass

    def apply_metadata_overrides(self, appinfo_manager) -> None:
        """
        Applies metadata overrides from AppInfoManager.

        This method first loads metadata from the binary appinfo.vdf (via AppInfoManager),
        then applies any custom user modifications stored in custom_metadata.json.

        Args:
            appinfo_manager: An instance of AppInfoManager with loaded appinfo.vdf data.
        """
        self.appinfo_manager = appinfo_manager
        modifications = appinfo_manager.load_appinfo()

        count = 0

        # 1. BINARY APPINFO METADATA
        for app_id, game in self.games.items():
            steam_meta = appinfo_manager.get_app_metadata(app_id)

            # Check for fallback name usage
            fallback_name = t('common.game_fallback', id=app_id)

            if (game.name == fallback_name or game.name.startswith("App ")) and steam_meta.get('name'):
                game.name = steam_meta['name']
                if not game.name_overridden:
                    game.sort_name = game.name

            if not game.developer and steam_meta.get('developer'):
                game.developer = steam_meta['developer']

            if not game.publisher and steam_meta.get('publisher'):
                game.publisher = steam_meta['publisher']

            if not game.release_year and steam_meta.get('release_date'):
                game.release_year = steam_meta['release_date']

        # 2. CUSTOM OVERRIDES
        for app_id, meta_data in modifications.items():
            if app_id in self.games:
                game = self.games[app_id]
                modified = meta_data.get('modified', {})

                if modified.get('name'):
                    game.name = modified['name']
                    game.name_overridden = True
                if modified.get('sort_as'):
                    game.sort_name = modified['sort_as']
                elif game.name_overridden:
                    game.sort_name = game.name
                if modified.get('developer'):
                    game.developer = modified['developer']
                if modified.get('publisher'):
                    game.publisher = modified['publisher']
                if modified.get('release_date'):
                    game.release_year = modified['release_date']

                count += 1

        if count > 0:
            print(t('logs.manager.applied_overrides', count=count))

    def get_all_games(self) -> List[Game]:
        """
        Returns all games sorted by sort_name.

        Returns:
            List[Game]: A list of all Game objects, sorted alphabetically by sort_name.
        """
        return sorted(list(self.games.values()), key=lambda g: g.sort_name.lower())

    def get_game(self, app_id: str) -> Optional[Game]:
        """
        Gets a single game by its app ID.

        Args:
            app_id (str): The Steam app ID.

        Returns:
            Optional[Game]: The Game object, or None if not found.
        """
        return self.games.get(app_id)

    def get_games_by_category(self, category: str) -> List[Game]:
        """
        Gets all games belonging to a specific category.

        Args:
            category (str): The category name.

        Returns:
            List[Game]: A sorted list of games in this category.
        """
        games = [g for g in self.games.values() if g.has_category(category)]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_uncategorized_games(self) -> List[Game]:
        """
        Gets games that have no category (excluding favorites).

        Returns:
            List[Game]: A sorted list of uncategorized games.
        """
        games = [g for g in self.games.values()
                 if not g.categories or g.categories == ['favorite']]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_favorites(self) -> List[Game]:
        """
        Gets all favorite games.

        Returns:
            List[Game]: A sorted list of favorite games.
        """
        games = [g for g in self.games.values() if g.is_favorite()]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_all_categories(self) -> Dict[str, int]:
        """
        Gets all categories and their game counts.

        Returns:
            Dict[str, int]: A dictionary mapping category names to game counts.
        """
        categories = {}
        for game in self.games.values():
            for category in game.categories:
                categories[category] = categories.get(category, 0) + 1
        return categories

    def fetch_game_details(self, app_id: str) -> bool:
        """
        Fetches additional details for a game from external APIs.

        This method fetches store data, review stats, and ProtonDB ratings
        for the specified game. The results are cached locally.

        Args:
            app_id (str): The Steam app ID.

        Returns:
            bool: True if the game exists, False otherwise.
        """
        if app_id not in self.games: return False
        self._fetch_store_data(app_id)
        self._fetch_review_stats(app_id)
        self._fetch_proton_rating(app_id)
        self._fetch_steam_deck_status(app_id)
        return True

    def _fetch_store_data(self, app_id: str) -> None:
        """
        Fetches and caches data from the Steam Store API.

        Args:
            app_id (str): The Steam app ID.
        """
        cache_file = self.cache_dir / 'store_data' / f'{app_id}.json'
        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=7):
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        self._apply_store_data(app_id, data)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            url = 'https://store.steampowered.com/api/appdetails'
            params = {'appids': app_id}
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            if app_id in data and data[app_id]['success']:
                game_data = data[app_id]['data']
                cache_file.parent.mkdir(exist_ok=True)
                with open(cache_file, 'w') as f:
                    json.dump(game_data, f)
                self._apply_store_data(app_id, game_data)
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    def _fetch_review_stats(self, app_id: str) -> None:
        """
        Fetches and caches Steam review statistics.

        Args:
            app_id (str): The Steam app ID.
        """
        cache_file = self.cache_dir / 'store_data' / f'{app_id}_reviews.json'
        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(hours=24):
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        self._apply_review_data(app_id, data)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            url = f'https://store.steampowered.com/appreviews/{app_id}?json=1&language=all'
            response = requests.get(url, timeout=5)
            data = response.json()
            if 'query_summary' in data:
                with open(cache_file, 'w') as f:
                    json.dump(data, f)
                self._apply_review_data(app_id, data)
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    def _fetch_proton_rating(self, app_id: str) -> None:
        """
        Fetches ProtonDB compatibility rating.

        Args:
            app_id (str): The Steam app ID.
        """
        cache_file = self.cache_dir / 'store_data' / f'{app_id}_proton.json'

        # Always use English tier names for internal storage (translated on display)
        unknown_status = "unknown"

        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=7):
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        if app_id in self.games:
                            self.games[app_id].proton_db_rating = data.get('tier', unknown_status)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            url = f'https://www.protondb.com/api/v1/reports/summaries/{app_id}.json'
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                tier = data.get('tier', unknown_status)
                with open(cache_file, 'w') as f:
                    json.dump({'tier': tier}, f)
                if app_id in self.games:
                    self.games[app_id].proton_db_rating = tier
            else:
                if app_id in self.games:
                    self.games[app_id].proton_db_rating = unknown_status
        except (requests.RequestException, ValueError, KeyError, OSError):
            if app_id in self.games:
                self.games[app_id].proton_db_rating = unknown_status

    def _fetch_steam_deck_status(self, app_id: str) -> None:
        """
        Fetches Steam Deck compatibility status from Valve's Deck API.

        Args:
            app_id (str): The Steam app ID.
        """
        cache_file = self.cache_dir / 'store_data' / f'{app_id}_deck.json'
        unknown_status = "unknown"

        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=7):
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        if app_id in self.games:
                            self.games[app_id].steam_deck_status = data.get('status', unknown_status)
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            # Use Valve's Steam Deck compatibility API
            url = f'https://store.steampowered.com/saleaction/ajaxgetdeckappcompatibilityreport?nAppID={app_id}'
            headers = {'User-Agent': 'SteamLibraryManager/1.0'}
            response = requests.get(url, timeout=5, headers=headers)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', {})

                # API sometimes returns a list instead of dict - handle both cases
                if isinstance(results, list):
                    # If it's a list, try to get the first element
                    results = results[0] if results else {}

                resolved_category = results.get('resolved_category', 0) if isinstance(results, dict) else 0

                # Steam Deck compatibility categories:
                # 0 = Unknown, 1 = Unsupported, 2 = Playable, 3 = Verified
                status_map = {0: 'unknown', 1: 'unsupported', 2: 'playable', 3: 'verified'}
                status = status_map.get(resolved_category, unknown_status)

                with open(cache_file, 'w') as f:
                    json.dump({'status': status, 'category': resolved_category}, f)
                if app_id in self.games:
                    self.games[app_id].steam_deck_status = status
                return

            if app_id in self.games:
                self.games[app_id].steam_deck_status = unknown_status
        except (requests.RequestException, ValueError, KeyError, OSError):
            if app_id in self.games:
                self.games[app_id].steam_deck_status = unknown_status

    def _apply_review_data(self, app_id: str, data: Dict) -> None:
        """
        Parses and applies review data to a game.

        Args:
            app_id (str): The Steam app ID.
            data (Dict): The review data from the Steam API.
        """
        if app_id not in self.games: return
        game = self.games[app_id]
        summary = data.get('query_summary', {})

        # Use t() for Unknown
        game.review_score = summary.get('review_score_desc', t('common.unknown'))

        game.review_count = summary.get('total_reviews', 0)

    def _apply_store_data(self, app_id: str, data: Dict) -> None:
        """
        Parses and applies store data to a game.

        Args:
            app_id (str): The Steam app ID.
            data (Dict): The store data from the Steam API.
        """
        game = self.games[app_id]
        if not game.name_overridden:
            game.developer = ', '.join(data.get('developers', []))
            game.publisher = ', '.join(data.get('publishers', []))
            release = data.get('release_date', {})
            if release.get('date'):
                game.release_year = release['date']
        genres = data.get('genres', [])
        game.genres = [g['description'] for g in genres]
        categories = data.get('categories', [])
        tags = [c['description'] for c in categories]
        game.tags = list(set(game.tags + tags))

    def get_load_source_message(self) -> str:
        """
        Returns a localized status message about the load source.

        Returns:
            str: A localized message indicating how games were loaded (API, local, or mixed).
        """
        if self.load_source == "api":
            return t('logs.manager.loaded_api', count=len(self.games))
        elif self.load_source == "local":
            return t('logs.manager.loaded_local', count=len(self.games))
        elif self.load_source == "mixed":
            return t('logs.manager.loaded_mixed', count=len(self.games))
        else:
            return t('ui.main_window.status_ready')
