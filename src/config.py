"""
Configuration - Cleaned, Typed & Warning-Free
Speichern als: src/config.py
"""
import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple

# FIX: Lambda nutzen, um 'unused parameter' Warnungen zu vermeiden
try:
    # noinspection PyPackageRequirements
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *args, **kwargs: None


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

    # API KEYS
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
        (self.APP_DIR / 'logs').mkdir(exist_ok=True)

        # Lade .env
        try:
            load_dotenv(Path(__file__).parent.parent / '.env')
        except (OSError, UnicodeDecodeError):
            pass

        # Lade Umgebungsvariablen
        if os.getenv('STEAM_API_KEY'):
            self.STEAM_API_KEY = os.getenv('STEAM_API_KEY')

        self._load_settings()

        if not self.STEAM_PATH:
            self.STEAM_PATH = self._find_steam_path()

    def _load_settings(self):
        if self.SETTINGS_FILE.exists():
            try:
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'ui_language' in data: self.UI_LANGUAGE = data['ui_language']
                if 'tags_language' in data: self.TAGS_LANGUAGE = data['tags_language']
                if 'steamgriddb_api_key' in data: self.STEAMGRIDDB_API_KEY = data['steamgriddb_api_key']
                if 'steam_path' in data and data['steam_path']:
                    self.STEAM_PATH = Path(data['steam_path'])
                if 'max_backups' in data: self.MAX_BACKUPS = data['max_backups']

            except (OSError, json.JSONDecodeError) as e:
                print(f"Error loading settings: {e}")

    def save_settings(self, **kwargs):
        current = {}
        if self.SETTINGS_FILE.exists():
            try:
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    current = json.load(f)
            except (OSError, json.JSONDecodeError):
                pass

        current.update(kwargs)
        if 'steam_path' in kwargs and isinstance(kwargs['steam_path'], Path):
            current['steam_path'] = str(kwargs['steam_path'])

        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(current, f, indent=2)
        except OSError as e:
            print(f"Error saving settings: {e}")

    @staticmethod
    def _find_steam_path() -> Optional[Path]:
        paths = [
            Path.home() / '.steam' / 'steam',
            Path.home() / '.local' / 'share' / 'Steam',
        ]
        for p in paths:
            if p.exists():
                # Folge Symlinks
                return p.resolve() if p.is_symlink() else p
        return None

    def get_detected_user(self) -> Tuple[Optional[str], Optional[str]]:
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
        if not self.STEAM_PATH or not account_id: return None
        return self.STEAM_PATH / 'userdata' / account_id / 'config' / 'localconfig.vdf'


# Globale Instanz
config = Config()