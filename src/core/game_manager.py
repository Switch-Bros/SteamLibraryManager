"""
Game Manager - Verwaltet alle Spiele und deren Daten
"""

import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime, timedelta


@dataclass
class Game:
    """Repräsentiert ein Steam-Spiel"""
    app_id: str
    name: str
    playtime_minutes: int = 0
    last_played: Optional[datetime] = None
    categories: List[str] = None

    # Metadaten (von Steam API oder überschrieben)
    developer: str = ""
    publisher: str = ""
    release_year: str = ""
    genres: List[str] = None
    tags: List[str] = None

    # Steam Deck
    deck_verified: Optional[bool] = None

    # Override-Flags
    name_overridden: bool = False

    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if self.genres is None:
            self.genres = []
        if self.tags is None:
            self.tags = []

    @property
    def playtime_hours(self) -> float:
        """Spielzeit in Stunden"""
        return round(self.playtime_minutes / 60, 1)

    def has_category(self, category: str) -> bool:
        """Prüfe ob Spiel in Kategorie ist"""
        return category in self.categories

    def is_favorite(self) -> bool:
        """Prüfe ob Favorit"""
        return 'favorite' in self.categories


class GameManager:
    """Verwaltet alle Spiele"""

    def __init__(self, steam_api_key: str, cache_dir: Path):
        self.api_key = steam_api_key
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

        self.games: Dict[str, Game] = {}
        self.steam_user_id: Optional[str] = None

    def load_from_steam_api(self, steam_user_id: str) -> bool:
        """
        Lade Spiele-Bibliothek von Steam API

        Args:
            steam_user_id: Steam User ID (z.B. "43925226")

        Returns:
            True wenn erfolgreich
        """
        self.steam_user_id = steam_user_id

        try:
            url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
            params = {
                'key': self.api_key,
                'steamid': steam_user_id,
                'include_appinfo': 1,
                'include_played_free_games': 1,
                'format': 'json'
            }

            print(f"Loading games from Steam API...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'response' not in data or 'games' not in data['response']:
                print("Error: No games found in API response")
                return False

            games_data = data['response']['games']
            print(f"✓ Loaded {len(games_data)} games from Steam")

            # Konvertiere zu Game-Objekten
            for game_data in games_data:
                app_id = str(game_data['appid'])

                game = Game(
                    app_id=app_id,
                    name=game_data.get('name', f'Game {app_id}'),
                    playtime_minutes=game_data.get('playtime_forever', 0)
                )

                self.games[app_id] = game

            return True

        except requests.exceptions.RequestException as e:
            print(f"Error loading from Steam API: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

    def merge_with_localconfig(self, parser):
        """
        Merge Spiele-Daten mit localconfig.vdf (Kategorien)

        Args:
            parser: LocalConfigParser Instanz
        """
        print("Merging with localconfig.vdf...")

        # Hole alle App IDs aus localconfig
        local_app_ids = set(parser.get_all_app_ids())

        # Merge Kategorien für bekannte Spiele
        for app_id in self.games:
            if app_id in local_app_ids:
                categories = parser.get_app_categories(app_id)
                self.games[app_id].categories = categories

        # Füge Spiele hinzu die nur in localconfig sind (nicht in Bibliothek)
        # Das können Non-Steam-Spiele oder gelöschte Spiele sein
        api_app_ids = set(self.games.keys())
        missing_ids = local_app_ids - api_app_ids

        if missing_ids:
            print(f"Found {len(missing_ids)} games in localconfig not in library")
            # Diese ignorieren wir vorerst

        print(f"✓ Merged categories for {len(self.games)} games")

    def get_all_games(self) -> List[Game]:
        """Hole alle Spiele als Liste"""
        return list(self.games.values())

    def get_game(self, app_id: str) -> Optional[Game]:
        """Hole einzelnes Spiel"""
        return self.games.get(app_id)

    def get_games_by_category(self, category: str) -> List[Game]:
        """Hole alle Spiele einer Kategorie"""
        return [g for g in self.games.values() if g.has_category(category)]

    def get_uncategorized_games(self) -> List[Game]:
        """Hole alle Spiele ohne Kategorien"""
        return [g for g in self.games.values()
                if not g.categories or g.categories == ['favorite']]

    def get_favorites(self) -> List[Game]:
        """Hole alle Favoriten"""
        return [g for g in self.games.values() if g.is_favorite()]

    def search_games(self, query: str) -> List[Game]:
        """
        Suche Spiele nach Namen

        Args:
            query: Suchbegriff

        Returns:
            Liste gefundener Spiele
        """
        query_lower = query.lower()
        return [g for g in self.games.values()
                if query_lower in g.name.lower()]

    def get_all_categories(self) -> Dict[str, int]:
        """
        Hole alle Kategorien mit Anzahl Spiele

        Returns:
            Dict: {category_name: game_count}
        """
        categories = {}

        for game in self.games.values():
            for category in game.categories:
                categories[category] = categories.get(category, 0) + 1

        return categories

    def fetch_game_details(self, app_id: str) -> bool:
        """
        Hole detaillierte Infos zu einem Spiel von Steam Store

        Args:
            app_id: Steam App ID

        Returns:
            True wenn erfolgreich
        """
        # Prüfe Cache
        cache_file = self.cache_dir / 'store_data' / f'{app_id}.json'

        if cache_file.exists():
            # Cache < 7 Tage alt?
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age < timedelta(days=7):
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    self._apply_store_data(app_id, data)
                    return True

        # Fetch von Steam Store
        try:
            url = f'https://store.steampowered.com/api/appdetails'
            params = {'appids': app_id}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if app_id in data and data[app_id]['success']:
                game_data = data[app_id]['data']

                # Cache speichern
                cache_file.parent.mkdir(exist_ok=True)
                with open(cache_file, 'w') as f:
                    json.dump(game_data, f)

                self._apply_store_data(app_id, game_data)
                return True

            return False

        except Exception as e:
            print(f"Error fetching details for {app_id}: {e}")
            return False

    def _apply_store_data(self, app_id: str, data: Dict):
        """Wende Store-Daten auf Game an"""
        if app_id not in self.games:
            return

        game = self.games[app_id]

        game.developer = ', '.join(data.get('developers', []))
        game.publisher = ', '.join(data.get('publishers', []))

        # Release year
        release_date = data.get('release_date', {})
        if release_date.get('date'):
            try:
                date_str = release_date['date']
                # Format: "15 Jan, 2025" oder nur "2025"
                if ',' in date_str:
                    game.release_year = date_str.split(',')[-1].strip()
                else:
                    game.release_year = date_str.strip()
            except:
                pass

        # Genres
        genres = data.get('genres', [])
        game.genres = [g['description'] for g in genres]

        # Categories (Steam's intern, nicht user-categories!)
        # Diese können wir für Tags nutzen
        categories = data.get('categories', [])
        steam_tags = [c['description'] for c in categories]

        # Merge mit existierenden Tags
        game.tags = list(set(game.tags + steam_tags))


# Beispiel-Nutzung
if __name__ == "__main__":
    from src.config import config
    from src.core.localconfig_parser import LocalConfigParser

    # Game Manager erstellen
    manager = GameManager(config.STEAM_API_KEY, config.CACHE_DIR)

    # Von Steam API laden (benötigt API Key!)
    if config.STEAM_API_KEY and config.STEAM_USER_ID:
        if manager.load_from_steam_api(config.STEAM_USER_ID):

            # Merge mit localconfig
            config_path = config.get_localconfig_path()
            if config_path:
                parser = LocalConfigParser(config_path)
                if parser.load():
                    manager.merge_with_localconfig(parser)

            # Statistiken
            print(f"\n📊 Statistics:")
            print(f"Total games: {len(manager.get_all_games())}")
            print(f"Favorites: {len(manager.get_favorites())}")
            print(f"Uncategorized: {len(manager.get_uncategorized_games())}")

            # Kategorien
            categories = manager.get_all_categories()
            print(f"\nCategories: {len(categories)}")
            for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
                print(f"  • {cat}: {count} games")