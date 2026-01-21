"""
Configuration - With Resources Path
Speichern als: src/config.py
"""
import os
import json
import base64
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Config:
    APP_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = APP_DIR / 'data'
    CACHE_DIR: Path = DATA_DIR / 'cache'
    # NEU: Pfad zu deinen Ressourcen
    RESOURCES_DIR: Path = APP_DIR / 'resources'
    ICONS_DIR: Path = RESOURCES_DIR / 'icons'

    SETTINGS_FILE: Path = DATA_DIR / 'settings.json'

    UI_LANGUAGE: str = 'en'
    TAGS_LANGUAGE: str = 'en'
    DEFAULT_LOCALE: str = 'en'

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
        self.DATA_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)
        (self.CACHE_DIR / 'game_tags').mkdir(exist_ok=True)
        (self.CACHE_DIR / 'store_data').mkdir(exist_ok=True)
        (self.CACHE_DIR / 'images').mkdir(exist_ok=True)

        # Resources Ordner erstellen, falls nicht existiert (damit keine Fehler kommen)
        self.ICONS_DIR.mkdir(parents=True, exist_ok=True)

        self._load_settings()

        if self.STEAM_PATH is None:
            self.STEAM_PATH = self._find_steam_path()

    def _get_obfuscated_key(self) -> str:
        ENCODED_KEY = "RDU4Q0NEM0UxMTBCRUIyNkRBODA0Njc3NDk3MzBCREI="
        try:
            return base64.b64decode(ENCODED_KEY).decode()
        except Exception:
            return ""

    def _get_sgdb_key(self) -> str:
        ENCODED_KEY = "OTZhOGY0ODczZjM3ZjJiZDU1Zjk5OGI0NTFiYTJlMzM="
        try:
            return base64.b64decode(ENCODED_KEY).decode()
        except Exception:
            return ""

    def _load_settings(self):
        self.STEAM_API_KEY = self._get_obfuscated_key()
        self.STEAMGRIDDB_API_KEY = self._get_sgdb_key()

        if self.SETTINGS_FILE.exists():
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)

                self.UI_LANGUAGE = settings.get('ui_language', 'en')
                self.TAGS_LANGUAGE = settings.get('tags_language', 'en')
                self.TAGS_PER_GAME = settings.get('tags_per_game', 13)
                self.IGNORE_COMMON_TAGS = settings.get('ignore_common_tags', True)

                if settings.get('steam_api_key'):
                    self.STEAM_API_KEY = settings.get('steam_api_key')

            except Exception as e:
                print(e)

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