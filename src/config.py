"""
Configuration - Windows & Linux Auto-Detection
Includes logic to parse Steam libraryfolders.vdf automatically.
Includes UI persistence for categories.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path

# Load environment variables silently
try:
    # noinspection PyPackageRequirements
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *args, **kwargs: None

logger = logging.getLogger("steamlibmgr.config")


__all__ = ["Config", "config"]


@dataclass
class Config:
    """
    Central configuration handling for the application.
    Manages paths, settings, API keys, and UI state.
    """

    APP_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = APP_DIR / "data"
    CACHE_DIR: Path = DATA_DIR / "cache"
    RESOURCES_DIR: Path = APP_DIR / "resources"
    ICONS_DIR: Path = RESOURCES_DIR / "icons"

    SETTINGS_FILE: Path = DATA_DIR / "settings.json"

    # Default values
    UI_LANGUAGE: str = "en"
    TAGS_LANGUAGE: str = "en"
    DEFAULT_LOCALE: str = "en"
    THEME: str = "dark"

    # API KEYS
    STEAM_API_KEY: str | None = None
    STEAMGRIDDB_API_KEY: str | None = None

    STEAM_PATH: Path | None = None
    STEAM_USER_ID: str | None = None
    STEAM_ACCESS_TOKEN: str | None = None  # Runtime-only, NOT persisted to JSON

    # List for additional libraries
    STEAM_LIBRARIES: list[str] = None

    # UI State: Which categories are expanded?
    EXPANDED_CATEGORIES: list[str] = None

    MAX_BACKUPS: int = 5
    TAGS_PER_GAME: int = 13
    IGNORE_COMMON_TAGS: bool = True

    def __post_init__(self):
        """Initialize directories and load settings after instantiation."""
        self.DATA_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)

        if self.STEAM_LIBRARIES is None:
            self.STEAM_LIBRARIES = []

        if self.EXPANDED_CATEGORIES is None:
            self.EXPANDED_CATEGORIES = []

        load_dotenv()
        env_key = os.getenv("STEAM_API_KEY")
        if env_key:
            self.STEAM_API_KEY = env_key

        self._load_settings()

        # Auto-Detect Steam Path if missing
        if not self.STEAM_PATH:
            detected = self._find_steam_path()
            if detected:
                self.STEAM_PATH = detected

        # Auto-Detect Libraries if empty
        if not self.STEAM_LIBRARIES and self.STEAM_PATH:
            self.STEAM_LIBRARIES = self._detect_library_folders()

    def _load_settings(self) -> None:
        """Load settings from JSON file."""
        # Local import to avoid circular dependency
        from src.utils.i18n import t

        if not self.SETTINGS_FILE.exists():
            return

        try:
            with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                self.UI_LANGUAGE = data.get("ui_language", self.UI_LANGUAGE)
                self.TAGS_LANGUAGE = data.get("tags_language", self.TAGS_LANGUAGE)

                steam_path = data.get("steam_path")
                if steam_path:
                    self.STEAM_PATH = Path(steam_path)

                self.STEAMGRIDDB_API_KEY = data.get("steamgriddb_api_key", self.STEAMGRIDDB_API_KEY)
                self.STEAM_API_KEY = data.get("steam_api_key", self.STEAM_API_KEY)
                self.TAGS_PER_GAME = data.get("tags_per_game", self.TAGS_PER_GAME)
                self.IGNORE_COMMON_TAGS = data.get("ignore_common_tags", self.IGNORE_COMMON_TAGS)
                self.MAX_BACKUPS = data.get("max_backups", self.MAX_BACKUPS)
                self.STEAM_LIBRARIES = data.get("steam_libraries", [])
                self.STEAM_USER_ID = data.get("steam_user_id")

                # Load UI State
                self.EXPANDED_CATEGORIES = data.get("expanded_categories", [])

        except (OSError, json.JSONDecodeError) as e:
            logger.error(t("logs.config.load_error", error=e))

    def save(self) -> None:
        """Save current configuration to JSON file."""
        # Local import to avoid circular dependency
        from src.utils.i18n import t

        data = {
            "ui_language": self.UI_LANGUAGE,
            "tags_language": self.TAGS_LANGUAGE,
            "steam_path": str(self.STEAM_PATH) if self.STEAM_PATH else "",
            "steamgriddb_api_key": self.STEAMGRIDDB_API_KEY,
            "steam_api_key": self.STEAM_API_KEY,
            "tags_per_game": self.TAGS_PER_GAME,
            "ignore_common_tags": self.IGNORE_COMMON_TAGS,
            "max_backups": self.MAX_BACKUPS,
            "steam_libraries": self.STEAM_LIBRARIES,
            "steam_user_id": self.STEAM_USER_ID,
            "expanded_categories": self.EXPANDED_CATEGORIES,
        }

        try:
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.error(t("logs.config.save_error", error=e))

    def update_paths(self, **kwargs) -> None:
        """Update paths and save configuration."""
        if "steam_path" in kwargs:
            self.STEAM_PATH = kwargs["steam_path"]
        self.save()

    @staticmethod
    def _find_steam_path() -> Path | None:
        """Auto-detect Steam path on Linux and Windows."""
        system = platform.system()

        if system == "Windows":
            try:
                import winreg

                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
                path_str, _ = winreg.QueryValueEx(key, "SteamPath")
                path = Path(path_str)
                if path.exists():
                    return path
            except OSError:
                # Fallback to standard paths if registry fails
                common_paths = [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]
                for p in common_paths:
                    if p.exists():
                        return p

        else:
            # Linux detection
            paths = [
                Path.home() / ".steam" / "steam",
                Path.home() / ".local" / "share" / "Steam",
            ]
            for p in paths:
                if p.exists():
                    return p.resolve() if p.is_symlink() else p

        return None

    def _detect_library_folders(self) -> list[str]:
        """Parses libraryfolders.vdf to find all steam library paths."""
        from src.utils.i18n import t

        if not self.STEAM_PATH:
            return []

        vdf_path = self.STEAM_PATH / "steamapps" / "libraryfolders.vdf"
        if not vdf_path.exists():
            return []

        libraries = set()
        libraries.add(str(self.STEAM_PATH))

        try:
            with open(vdf_path, "r", encoding="utf-8") as f:
                content = f.read()
                matches = re.findall(r'"path"\s+"([^"]+)"', content)
                for path in matches:
                    path = path.replace("\\\\", "\\")
                    libraries.add(path)
        except Exception as e:
            logger.error(t("logs.config.library_read_error", error=e))

        return list(libraries)

    def get_detected_user(self) -> tuple[str | None, str | None]:
        if not self.STEAM_PATH:
            return None, None
        userdata = self.STEAM_PATH / "userdata"
        if not userdata.exists():
            return None, None

        for item in userdata.iterdir():
            if item.is_dir() and item.name.isdigit():
                if (item / "config" / "localconfig.vdf").exists():
                    account_id = int(item.name)
                    steam_id_64 = str(account_id + 76561197960265728)
                    return str(account_id), steam_id_64
        return None, None

    def get_localconfig_path(self, account_id: str) -> Path | None:
        if not self.STEAM_PATH or not account_id:
            return None
        return self.STEAM_PATH / "userdata" / account_id / "config" / "localconfig.vdf"


# Global instance
config = Config()
