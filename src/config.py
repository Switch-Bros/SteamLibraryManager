"""
Configuration - Steam API Key is now optional
Speichern als: src/config.py
"""
import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple
from dotenv import load_dotenv

# Lade .env Datei (für Entwicklung)
load_dotenv(Path(__file__).parent.parent / '.env')


@dataclass
class Config:
    APP_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = APP_DIR / 'data'
    CACHE_DIR: Path = DATA_DIR / 'cache'
    RESOURCES_DIR: Path = APP_DIR / 'resources'
    ICONS_DIR: Path = RESOURCES_DIR / 'icons'

    SETTINGS_FILE: Path = DATA_DIR / 'settings.json'

    # Standardwerte
    UI_LANGUAGE: str = 'en'
    TAGS_LANGUAGE: str = 'en'
    DEFAULT_LOCALE: str = 'en'
    THEME: str = 'dark'

    # API KEYS (BEIDE OPTIONAL!)
    STEAM_API_KEY: Optional[str] = None
    STEAMGRIDDB_API_KEY: Optional[str] = None

    STEAM_PATH: Optional[Path] = None
    STEAM_USER_ID: Optional[str] = None
    MAX_BACKUPS: int = 5
    TAGS_PER_GAME: int = 13
    IGNORE_COMMON_TAGS: bool = True

    def __post_init__(self):
        self.DATA_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)
        (self.CACHE_DIR / 'game_tags').mkdir(exist_ok=True)
        (self.CACHE_DIR / 'store_data').mkdir(exist_ok=True)
        (self.CACHE_DIR / 'images').mkdir(exist_ok=True)
        self.ICONS_DIR.mkdir(parents=True, exist_ok=True)

        self._load_settings()

        # Fallback: Environment Variables (Dev Mode)
        if not self.STEAM_API_KEY:
            env_key = os.getenv("STEAM_API_KEY")
            if env_key:
                self.STEAM_API_KEY = env_key

        if not self.STEAMGRIDDB_API_KEY:
            env_key = os.getenv("STEAMGRIDDB_API_KEY")
            if env_key:
                self.STEAMGRIDDB_API_KEY = env_key

        if self.STEAM_PATH is None:
            self.STEAM_PATH = self._find_steam_path()

    def _load_settings(self):
        from src.utils.i18n import t

        if self.SETTINGS_FILE.exists():
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)

                self.UI_LANGUAGE = settings.get('ui_language', 'en')
                self.TAGS_LANGUAGE = settings.get('tags_language', 'en')
                self.TAGS_PER_GAME = settings.get('tags_per_game', 13)
                self.IGNORE_COMMON_TAGS = settings.get('ignore_common_tags', True)
                self.MAX_BACKUPS = settings.get('max_backups', 5)

                # API Keys aus Settings (User kann beide eingeben!)
                if settings.get('steamgriddb_api_key'):
                    self.STEAMGRIDDB_API_KEY = settings.get('steamgriddb_api_key')

                if settings.get('steam_api_key'):
                    self.STEAM_API_KEY = settings.get('steam_api_key')

            except Exception as e:
                print(t('logs.config.error', error=e))

    def save_settings(self, **kwargs):
        current = {}
        if self.SETTINGS_FILE.exists():
            with open(self.SETTINGS_FILE, 'r') as f:
                current = json.load(f)
        current.update(kwargs)
        with open(self.SETTINGS_FILE, 'w') as f:
            json.dump(current, f, indent=2)

    def _find_steam_path(self) -> Optional[Path]:
        paths = [
            Path.home() / '.steam' / 'steam',
            Path.home() / '.local' / 'share' / 'Steam',
        ]
        for p in paths:
            if p.exists():
                return p
        return None

    def get_detected_user(self) -> Tuple[Optional[str], Optional[str]]:
        """Versucht User lokal zu finden (Fallback)"""
        if not self.STEAM_PATH: return None, None
        userdata = self.STEAM_PATH / 'userdata'
        if not userdata.exists(): return None, None

        for item in userdata.iterdir():
            if item.is_dir() and item.name.isdigit():
                if (item / 'config' / 'localconfig.vdf').exists():
                    account_id = int(item.name)
                    steam_id_64 = str(account_id + 76561197960265728)
                    return str(account_id), steam_id_64
        return None, None

    def get_localconfig_path(self, account_id: str) -> Optional[Path]:
        if self.STEAM_PATH and account_id:
            return self.STEAM_PATH / 'userdata' / account_id / 'config' / 'localconfig.vdf'
        return None


config = Config()