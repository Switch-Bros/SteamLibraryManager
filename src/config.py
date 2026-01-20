"""
Configuration - Auto-Detect SteamID
Speichern als: src/config.py
"""
import os
import json
import base64
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class Config:
    APP_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = APP_DIR / 'data'
    CACHE_DIR: Path = DATA_DIR / 'cache'
    SETTINGS_FILE: Path = DATA_DIR / 'settings.json'

    # Defaults
    UI_LANGUAGE: str = 'en'
    TAGS_LANGUAGE: str = 'en'
    DEFAULT_LOCALE: str = 'en'

    # Keys
    STEAM_API_KEY: str = ''
    STEAMGRIDDB_API_KEY: str = ''

    # Paths & IDs
    STEAM_PATH: Optional[Path] = None
    STEAM_USER_ID: Optional[str] = None  # Wird jetzt dynamisch gesetzt

    # Settings
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

        self._load_settings()

        if self.STEAM_PATH is None:
            self.STEAM_PATH = self._find_steam_path()

    def _get_obfuscated_key(self) -> str:
        # Dein verschlüsselter Key
        ENCODED_KEY = "RDU4Q0NEM0UxMTBCRUIyNkRBODA0Njc3NDk3MzBCREI="
        try:
            return base64.b64decode(ENCODED_KEY).decode()
        except Exception:
            return ""

    def _load_settings(self):
        # 1. Standard Key laden
        self.STEAM_API_KEY = self._get_obfuscated_key()

        if self.SETTINGS_FILE.exists():
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)

                self.UI_LANGUAGE = settings.get('ui_language', 'en')
                self.TAGS_LANGUAGE = settings.get('tags_language', 'en')
                self.TAGS_PER_GAME = settings.get('tags_per_game', 13)
                self.IGNORE_COMMON_TAGS = settings.get('ignore_common_tags', True)

                # Wenn User manuell einen Key eingegeben hat, nimm den
                if settings.get('steam_api_key'):
                    self.STEAM_API_KEY = settings.get('steam_api_key')

            except Exception as e:
                print(f"Error loading settings: {e}")

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
        """
        Versucht den lokalen User zu erkennen.
        Returns: (AccountID_Short, SteamID64_Long)
        """
        if not self.STEAM_PATH:
            return None, None

        userdata = self.STEAM_PATH / 'userdata'
        if not userdata.exists():
            return None, None

        # Nimm den ersten Ordner, der eine localconfig hat
        for item in userdata.iterdir():
            if item.is_dir() and item.name.isdigit():
                if (item / 'config' / 'localconfig.vdf').exists():
                    account_id = int(item.name)
                    # ✨ MAGIE: Umrechnung ShortID -> SteamID64
                    steam_id_64 = str(account_id + 76561197960265728)
                    return str(account_id), steam_id_64

        return None, None

    def get_localconfig_path(self, account_id: str) -> Optional[Path]:
        if self.STEAM_PATH and account_id:
            return self.STEAM_PATH / 'userdata' / account_id / 'config' / 'localconfig.vdf'
        return None


config = Config()