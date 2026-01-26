"""
Configuration - Cleaned, Typed & Localized
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
    # Liste für zusätzliche Bibliotheken
    STEAM_LIBRARIES: list = None

    MAX_BACKUPS: int = 5
    TAGS_PER_GAME: int = 13
    IGNORE_COMMON_TAGS: bool = True

    def __post_init__(self):
        self.DATA_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)

        if self.STEAM_LIBRARIES is None:
            self.STEAM_LIBRARIES = []

        load_dotenv()
        env_key = os.getenv("STEAM_API_KEY")
        if env_key:
            self.STEAM_API_KEY = env_key

        self._load_settings()

        if not self.STEAM_PATH:
            detected = self._find_steam_path()
            if detected:
                self.STEAM_PATH = detected

    def _load_settings(self):
        # Local import to avoid circular dependency
        from src.utils.i18n import t

        if not self.SETTINGS_FILE.exists():
            return

        try:
            with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

                self.UI_LANGUAGE = data.get('ui_language', self.UI_LANGUAGE)
                self.TAGS_LANGUAGE = data.get('tags_language', self.TAGS_LANGUAGE)

                steam_path = data.get('steam_path')
                if steam_path:
                    self.STEAM_PATH = Path(steam_path)

                self.STEAMGRIDDB_API_KEY = data.get('steamgriddb_api_key', self.STEAMGRIDDB_API_KEY)
                self.STEAM_API_KEY = data.get('steam_api_key', self.STEAM_API_KEY)
                self.TAGS_PER_GAME = data.get('tags_per_game', self.TAGS_PER_GAME)
                self.IGNORE_COMMON_TAGS = data.get('ignore_common_tags', self.IGNORE_COMMON_TAGS)
                self.MAX_BACKUPS = data.get('max_backups', self.MAX_BACKUPS)
                self.STEAM_LIBRARIES = data.get('steam_libraries', [])

                # WICHTIG: User ID laden
                self.STEAM_USER_ID = data.get('steam_user_id')

        except (OSError, json.JSONDecodeError) as e:
            # Jetzt lokalisiert
            print(t('logs.config.load_error', error=e))

    def save(self):
        """Helper to save current config to file"""
        # Local import to avoid circular dependency
        from src.utils.i18n import t

        data = {
            'ui_language': self.UI_LANGUAGE,
            'tags_language': self.TAGS_LANGUAGE,
            'steam_path': str(self.STEAM_PATH) if self.STEAM_PATH else "",
            'steamgriddb_api_key': self.STEAMGRIDDB_API_KEY,
            'steam_api_key': self.STEAM_API_KEY,
            'tags_per_game': self.TAGS_PER_GAME,
            'ignore_common_tags': self.IGNORE_COMMON_TAGS,
            'max_backups': self.MAX_BACKUPS,
            'steam_libraries': self.STEAM_LIBRARIES,
            'steam_user_id': self.STEAM_USER_ID
        }

        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            # Jetzt lokalisiert
            print(t('logs.config.save_error', error=e))

    def update_paths(self, **kwargs):
        if 'steam_path' in kwargs:
            self.STEAM_PATH = kwargs['steam_path']

        self.save()

    @staticmethod
    def _find_steam_path() -> Optional[Path]:
        paths = [
            Path.home() / '.steam' / 'steam',
            Path.home() / '.local' / 'share' / 'Steam',
        ]
        for p in paths:
            if p.exists():
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


# Global instance
config = Config()