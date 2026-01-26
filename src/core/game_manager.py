"""
Game Manager - Full Featured, Cleaned & Type-Safe
Speichern als: src/core/game_manager.py
"""

import requests
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime, timedelta
from src.utils.i18n import t


@dataclass
class Game:
    """Repräsentiert ein Steam-Spiel"""
    app_id: str
    name: str
    playtime_minutes: int = 0
    last_played: Optional[datetime] = None
    categories: List[str] = None

    # Metadaten
    developer: str = ""
    publisher: str = ""
    release_year: str = ""
    genres: List[str] = None
    tags: List[str] = None

    # Sortierung
    sort_name: str = ""

    # Override-Flags
    name_overridden: bool = False

    # Erweiterte Daten
    proton_db_rating: str = ""
    steam_db_rating: str = ""
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
        if self.categories is None: self.categories = []
        if self.genres is None: self.genres = []
        if self.tags is None: self.tags = []

        if not self.sort_name:
            self.sort_name = self.name

    @property
    def playtime_hours(self) -> float:
        return round(self.playtime_minutes / 60, 1)

    def has_category(self, category: str) -> bool:
        return category in self.categories

    def is_favorite(self) -> bool:
        return 'favorite' in self.categories


class GameManager:
    def __init__(self, steam_api_key: Optional[str], cache_dir: Path, steam_path: Path):
        self.api_key = steam_api_key
        self.cache_dir = cache_dir
        self.steam_path = steam_path
        self.cache_dir.mkdir(exist_ok=True)

        self.games: Dict[str, Game] = {}
        self.steam_user_id: Optional[str] = None
        self.load_source: str = "unknown"
        self.appinfo_manager = None

    def load_games(self, steam_user_id: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Lädt Spiele mit Progress-Callback
        """
        self.steam_user_id = steam_user_id
        api_success = False

        # SCHRITT 1: Steam Web API
        if self.api_key:
            if progress_callback:
                progress_callback(t('ui.loading.trying_api'), 0, 3)

            print(t('logs.manager.trying_api'))
            api_success = self.load_from_steam_api(steam_user_id)

        # SCHRITT 2: Lokale Dateien
        if progress_callback:
            progress_callback(t('ui.loading.loading_local'), 1, 3)

        print(t('logs.manager.loading_local'))

        local_success = self.load_from_local_files(progress_callback)

        # SCHRITT 3: Status
        if progress_callback:
            progress_callback(t('ui.loading.finalizing'), 2, 3)

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
            progress_callback(t('ui.loading.complete'), 3, 3)

        return True

    def load_from_local_files(self, progress_callback: Optional[Callable] = None) -> bool:
        """Lädt Spiele aus lokalen Steam-Dateien"""
        from src.core.local_games_loader import LocalGamesLoader

        try:
            loader = LocalGamesLoader(self.steam_path)

            # Lade ALLE Spiele (installiert + aus appinfo.vdf)
            games_data = loader.get_all_games()

            if not games_data:
                print(t('logs.manager.no_local_games'))
                return False

            # Lade Playtime aus localconfig
            short_id, _ = self._get_user_ids()
            if short_id:
                from src.config import config
                localconfig_path = config.get_localconfig_path(short_id)
                playtimes = loader.get_playtime_from_localconfig(localconfig_path)
            else:
                playtimes = {}

            total = len(games_data)
            for i, game_data in enumerate(games_data):
                if progress_callback and i % 50 == 0:
                    progress_callback(t('ui.loading.processing_games'), i, total)

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
        """Lädt Spiele von Steam Web API"""
        if not self.api_key:
            print(t('logs.manager.no_api_key'))
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

            print(t('logs.manager.loading_api'))
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'response' not in data or 'games' not in data['response']:
                print(t('logs.manager.error_no_games'))
                return False

            games_data = data['response']['games']
            print(t('logs.manager.loaded_steam', count=len(games_data)))

            for game_data in games_data:
                app_id = str(game_data['appid'])
                original_name = game_data.get('name', f'Game {app_id}')

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

    @staticmethod
    def _get_user_ids() -> Tuple[Optional[str], Optional[str]]:
        from src.config import config
        return config.get_detected_user()

    def apply_metadata_overrides(self, appinfo_manager):
        """
        Apply metadata from AppInfo & custom modifications

        WICHTIG: Diese Methode wurde gefixt um:
        1. Release Date korrekt zu setzen (fehlte vorher!)
        2. Verschachtelung zu korrigieren (Performance)
        """
        self.appinfo_manager = appinfo_manager
        modifications = appinfo_manager.load_appinfo()

        count = 0

        # ========================================================================
        # 1. BINARY APPINFO METADATEN FÜR ALLE SPIELE
        # ========================================================================
        # Hier laden wir Developer/Publisher/Release aus der appinfo.vdf

        for app_id, game in self.games.items():
            # Hole Metadaten aus AppInfo
            steam_meta = appinfo_manager.get_app_metadata(app_id)

            # Name (nur für "App XXXXX" Fälle überschreiben)
            if game.name.startswith("App ") and steam_meta.get('name'):
                game.name = steam_meta['name']
                if not game.name_overridden:
                    game.sort_name = game.name

            # Developer (wenn noch leer/unbekannt)
            if not game.developer and steam_meta.get('developer'):
                game.developer = steam_meta['developer']

            # Publisher (wenn noch leer/unbekannt)
            if not game.publisher and steam_meta.get('publisher'):
                game.publisher = steam_meta['publisher']

            # ⚠️ FIX: Release Date wurde vorher NICHT gesetzt!
            if not game.release_year and steam_meta.get('release_date'):
                game.release_year = steam_meta['release_date']

        # ========================================================================
        # 2. CUSTOM OVERRIDES AUS custom_metadata.json
        # ========================================================================
        # ⚠️ FIX: Diese Schleife war vorher FALSCH verschachtelt!
        #    Sie war INNERHALB der Spiele-Schleife → Performance-Killer!

        for app_id, meta_data in modifications.items():
            if app_id in self.games:
                game = self.games[app_id]

                # Hole modified values aus dem modifications dict
                modified = meta_data.get('modified', {})

                # Name Override
                if modified.get('name'):
                    game.name = modified['name']
                    game.name_overridden = True

                # Sort Name Override
                if modified.get('sort_as'):
                    game.sort_name = modified['sort_as']
                elif game.name_overridden:
                    game.sort_name = game.name

                # Developer Override
                if modified.get('developer'):
                    game.developer = modified['developer']

                # Publisher Override
                if modified.get('publisher'):
                    game.publisher = modified['publisher']

                # Release Date Override
                if modified.get('release_date'):
                    game.release_year = modified['release_date']

                count += 1

        if count > 0:
            print(t('logs.manager.applied_overrides', count=count))

    def merge_with_localconfig(self, parser):
        print(t('logs.manager.merging'))
        local_app_ids = set(parser.get_all_app_ids())

        for app_id in self.games:
            if app_id in local_app_ids:
                categories = parser.get_app_categories(app_id)
                self.games[app_id].categories = categories

        api_app_ids = set(self.games.keys())
        missing_ids = local_app_ids - api_app_ids

        if missing_ids:
            print(t('logs.manager.found_missing', count=len(missing_ids)))
            for app_id in missing_ids:
                name = self._get_cached_name(app_id) or f"App {app_id}"

                game = Game(app_id=app_id, name=name)
                game.categories = parser.get_app_categories(app_id)
                self.games[app_id] = game

        print(t('logs.manager.merged', count=len(self.games)))

    def _get_cached_name(self, app_id: str) -> Optional[str]:
        cache_file = self.cache_dir / 'store_data' / f'{app_id}.json'
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    return data.get('name')
            except (OSError, json.JSONDecodeError):
                pass
        return None

    def apply_appinfo_data(self, appinfo_data: Dict):
        for app_id, data in appinfo_data.items():
            if app_id in self.games:
                if 'common' in data and 'last_updated' in data['common']:
                    ts = data['common']['last_updated']
                    try:
                        dt = datetime.fromtimestamp(int(ts))
                        self.games[app_id].last_updated = dt.strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass

    def get_all_games(self) -> List[Game]:
        return sorted(list(self.games.values()), key=lambda g: g.sort_name.lower())

    def get_game(self, app_id: str) -> Optional[Game]:
        return self.games.get(app_id)

    def get_games_by_category(self, category: str) -> List[Game]:
        games = [g for g in self.games.values() if g.has_category(category)]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_uncategorized_games(self) -> List[Game]:
        games = [g for g in self.games.values()
                 if not g.categories or g.categories == ['favorite']]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_favorites(self) -> List[Game]:
        games = [g for g in self.games.values() if g.is_favorite()]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_all_categories(self) -> Dict[str, int]:
        categories = {}
        for game in self.games.values():
            for category in game.categories:
                categories[category] = categories.get(category, 0) + 1
        return categories

    def fetch_game_details(self, app_id: str) -> bool:
        if app_id not in self.games: return False
        self._fetch_store_data(app_id)
        self._fetch_review_stats(app_id)
        self._fetch_proton_rating(app_id)
        return True

    def _fetch_store_data(self, app_id: str):
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
        # FIX Line 363: Spezifische Exceptions
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    def _fetch_review_stats(self, app_id: str):
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
        # FIX Line 387: Spezifische Exceptions
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    def _fetch_proton_rating(self, app_id: str):
        cache_file = self.cache_dir / 'store_data' / f'{app_id}_proton.json'
        if cache_file.exists():
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=7):
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        if app_id in self.games:
                            self.games[app_id].proton_db_rating = data.get('tier', 'unknown')
                    return
            except (OSError, json.JSONDecodeError):
                pass

        try:
            url = f'https://www.protondb.com/api/v1/reports/summaries/{app_id}.json'
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                tier = data.get('tier', 'unknown')
                with open(cache_file, 'w') as f:
                    json.dump({'tier': tier}, f)
                if app_id in self.games:
                    self.games[app_id].proton_db_rating = tier
            else:
                if app_id in self.games:
                    self.games[app_id].proton_db_rating = 'unknown'
        # FIX Line 417: Spezifische Exceptions
        except (requests.RequestException, ValueError, KeyError, OSError):
            pass

    def _apply_review_data(self, app_id: str, data: Dict):
        if app_id not in self.games: return
        game = self.games[app_id]
        summary = data.get('query_summary', {})
        game.review_score = summary.get('review_score_desc', 'Unknown')
        game.review_count = summary.get('total_reviews', 0)
        positive = summary.get('total_positive', 0)
        total = summary.get('total_reviews', 0)
        if total > 0:
            percent = (positive / total) * 100
            game.steam_db_rating = f"{percent:.0f}%"

    def _apply_store_data(self, app_id: str, data: Dict):
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
        if self.load_source == "api":
            return t('ui.status.loaded_from_api', count=len(self.games))
        elif self.load_source == "local":
            return t('ui.status.loaded_from_local', count=len(self.games))
        elif self.load_source == "mixed":
            return t('ui.status.loaded_mixed', count=len(self.games))
        else:
            return t('ui.status.ready')