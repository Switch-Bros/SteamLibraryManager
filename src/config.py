"""
Configuration - DEUTSCH als Default, KEINE .env nötig!

Speichern als: src/config.py
"""
import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    APP_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = APP_DIR / 'data'
    CACHE_DIR: Path = DATA_DIR / 'cache'
    SETTINGS_FILE: Path = DATA_DIR / 'settings.json'

    # ✨ DEUTSCH als Default!
    UI_LANGUAGE: str = 'de'
    TAGS_LANGUAGE: str = 'de'

    # Legacy (für Kompatibilität)
    DEFAULT_LOCALE: str = 'de'

    STEAM_API_KEY: str = ''
    STEAMGRIDDB_API_KEY: str = ''

    STEAM_PATH: Optional[Path] = None
    STEAM_USER_ID: Optional[str] = None

    THEME: str = 'dark'
    WINDOW_WIDTH: int = 1400
    WINDOW_HEIGHT: int = 800

    TAGS_PER_GAME: int = 13
    IGNORE_COMMON_TAGS: bool = True

    def __post_init__(self):
        # Create directories
        self.DATA_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)
        (self.CACHE_DIR / 'game_tags').mkdir(exist_ok=True)
        (self.CACHE_DIR / 'store_data').mkdir(exist_ok=True)

        # Load settings from file (NOT .env!)
        self._load_settings()

        # Find Steam
        if self.STEAM_PATH is None:
            self.STEAM_PATH = self._find_steam_path()

    def _load_settings(self):
        """Lade Settings aus JSON Datei"""
        if self.SETTINGS_FILE.exists():
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)

                # Apply settings
                self.UI_LANGUAGE = settings.get('ui_language', 'de')
                self.TAGS_LANGUAGE = settings.get('tags_language', 'de')
                self.TAGS_PER_GAME = settings.get('tags_per_game', 13)
                self.IGNORE_COMMON_TAGS = settings.get('ignore_common_tags', True)
                self.STEAM_USER_ID = settings.get('steam_user_id', None)
                self.STEAM_API_KEY = settings.get('steam_api_key', '')

                # Update DEFAULT_LOCALE for compatibility
                self.DEFAULT_LOCALE = self.UI_LANGUAGE

                print(f"✓ Settings loaded: UI={self.UI_LANGUAGE}, Tags={self.TAGS_LANGUAGE}")
            except Exception as e:
                print(f"Error loading settings: {e}")
        else:
            print("ℹ️ No settings file, using defaults (Deutsch)")

    def save_settings(self, **kwargs):
        """Speichere Settings in JSON Datei"""
        # Lade aktuelle Settings
        current = {}
        if self.SETTINGS_FILE.exists():
            with open(self.SETTINGS_FILE, 'r') as f:
                current = json.load(f)

        # Update
        current.update(kwargs)

        # Speichern
        with open(self.SETTINGS_FILE, 'w') as f:
            json.dump(current, f, indent=2)

    def _find_steam_path(self) -> Optional[Path]:
        """Finde Steam Installation auf Linux"""
        paths = [
            Path.home() / '.steam' / 'steam',
            Path.home() / '.local' / 'share' / 'Steam',
        ]
        for p in paths:
            if p.exists():
                return p
        return None

    def get_localconfig_path(self, user_id: Optional[str] = None) -> Optional[Path]:
        """
        Pfad zur localconfig.vdf für einen User

        Args:
            user_id: Steam User ID (optional, nutzt gespeicherte ID falls None)

        Returns:
            Path zur localconfig.vdf oder None
        """
        if user_id is None:
            user_id = self.STEAM_USER_ID

        if self.STEAM_PATH and user_id:
            config_path = self.STEAM_PATH / 'userdata' / user_id / 'config' / 'localconfig.vdf'
            if config_path.exists():
                return config_path

        return None

    def get_all_user_ids(self) -> list:
        """Finde alle Steam User IDs im userdata Ordner"""
        if not self.STEAM_PATH:
            return []

        userdata = self.STEAM_PATH / 'userdata'
        if not userdata.exists():
            return []

        ids = []
        for item in userdata.iterdir():
            if item.is_dir() and item.name.isdigit():
                if (item / 'config' / 'localconfig.vdf').exists():
                    ids.append(item.name)
        return ids

config = Config()