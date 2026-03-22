#
# steam_library_manager/config.py
# Application configuration with Steam auto-detection
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# FIXME: config is getting too fat

from __future__ import annotations

import logging
import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path

from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.json_utils import load_json, save_json
from steam_library_manager.utils.paths import get_resources_dir

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
    """Central configuration handling for the application."""

    APP_DIR: Path = Path(__file__).parent.parent
    RESOURCES_DIR: Path = get_resources_dir()
    ICONS_DIR: Path = RESOURCES_DIR / "icons"

    # DATA_DIR must be writable — XDG Base Directory Specification
    # Works for all installation types: AUR/native, Flatpak (remaps XDG), AppImage
    DATA_DIR: Path = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "steamlibrarymanager"
    CACHE_DIR: Path = DATA_DIR / "cache"
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

    # Update Settings
    UPDATE_CHECK_ON_STARTUP: bool = True
    UPDATE_CHECK_INTERVAL: str = "weekly"  # "never", "daily", "weekly", "monthly"
    UPDATE_LAST_CHECK: str = ""  # ISO timestamp
    UPDATE_SKIPPED_VERSION: str = ""  # User chose to skip this version

    def __post_init__(self):
        # init dirs and load settings
        self._migrate_legacy_data_dir()
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

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
            found = self._find_steam_path()
            if found:
                self.STEAM_PATH = found
                logger.info(t("logs.config.auto_detected", path=found, type=self.installation_type))

        # Auto-Detect Libraries if empty
        if not self.STEAM_LIBRARIES and self.STEAM_PATH:
            self.STEAM_LIBRARIES = self._detect_library_folders()

        # Always sync: remove dead paths, add new ones from Steam
        if self.STEAM_PATH:
            self._sync_library_folders()

    @property
    def installation_type(self) -> str:
        if not self.STEAM_PATH:
            return "unknown"

        ps = str(self.STEAM_PATH).lower()

        if "flatpak" in ps or ".var/app/com.valvesoftware.steam" in ps:
            return "flatpak"
        elif ".steam" in ps or ".local/share/steam" in ps:
            return "native"
        elif "program files" in ps:
            return "native"
        else:
            return "custom"

    @property
    def grid_folder(self) -> Path | None:
        # steam grid folder path
        if not self.STEAM_PATH:
            return None

        short_id, _ = self.get_detected_user()
        if not short_id:
            return None

        grid_path = self.STEAM_PATH / "userdata" / short_id / "config" / "grid"

        # Create if doesn't exist
        grid_path.mkdir(parents=True, exist_ok=True)

        return grid_path

    def _migrate_legacy_data_dir(self) -> None:
        # move pre-v1.2 data to XDG location
        legacy_data_dir = Path(__file__).resolve().parent.parent / "data"
        if legacy_data_dir.is_dir() and not self.DATA_DIR.is_dir():
            import shutil

            logger.info("Migrating data from %s to %s" % (legacy_data_dir, self.DATA_DIR))
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copytree(legacy_data_dir, self.DATA_DIR, dirs_exist_ok=True)
            logger.info("Data migration complete")

    def _load_settings(self) -> None:
        # load from json
        data = load_json(self.SETTINGS_FILE)
        if not data:
            return

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

        # Load Update Settings
        self.UPDATE_CHECK_ON_STARTUP = data.get("update_check_on_startup", self.UPDATE_CHECK_ON_STARTUP)
        self.UPDATE_CHECK_INTERVAL = data.get("update_check_interval", self.UPDATE_CHECK_INTERVAL)
        self.UPDATE_LAST_CHECK = data.get("update_last_check", self.UPDATE_LAST_CHECK)
        self.UPDATE_SKIPPED_VERSION = data.get("update_skipped_version", self.UPDATE_SKIPPED_VERSION)

    def save(self) -> None:
        # persist to json
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
            "update_check_on_startup": self.UPDATE_CHECK_ON_STARTUP,
            "update_check_interval": self.UPDATE_CHECK_INTERVAL,
            "update_last_check": self.UPDATE_LAST_CHECK,
            "update_skipped_version": self.UPDATE_SKIPPED_VERSION,
        }

        save_json(self.SETTINGS_FILE, data, restrict_permissions=True)

    def update_paths(self, **kwargs) -> None:
        if "steam_path" in kwargs:
            self.STEAM_PATH = Path(kwargs["steam_path"]) if kwargs["steam_path"] else None
        self.save()

    @staticmethod
    def _find_steam_path() -> Path | None:
        # auto-detect steam on linux/windows
        system = platform.system()

        if system == "Windows":
            try:
                import winreg

                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
                ps, _ = winreg.QueryValueEx(key, "SteamPath")
                path = Path(ps)
                if path.exists():
                    logger.info(t("logs.config.found_via_registry", path=path))
                    return path
            except OSError:
                pass

            # Fallback to standard paths
            paths = [
                Path(r"C:\Program Files (x86)\Steam"),
                Path(r"C:\Program Files\Steam"),
                Path(r"D:\Steam"),
                Path(r"E:\Steam"),
            ]
            for p in paths:
                if p.exists():
                    logger.info(t("logs.config.found_at", path=p))
                    return p

        else:
            # Linux/SteamOS detection
            home = Path.home()

            # Check Flatpak FIRST (most common on Deck/modern Linux)
            fpak = home / ".var/app/com.valvesoftware.Steam/.local/share/Steam"
            if fpak.exists():
                logger.info(t("logs.config.found_flatpak", path=fpak))
                return fpak

            # Check Native Steam
            paths = [
                home / ".local/share/Steam",  # Standard location
                home / ".steam/steam",  # Symlink/legacy
                home / "Steam",  # Custom
            ]

            for p in paths:
                if p.exists():
                    # Resolve symlinks
                    resolved = p.resolve() if p.is_symlink() else p
                    logger.info(t("logs.config.found_native", path=resolved))
                    return resolved

        logger.warning(t("logs.config.not_found"))
        return None

    def _sync_library_folders(self) -> None:
        # sync with libraryfolders.vdf
        found = self._detect_library_folders()
        if not found:
            return

        saved = set(self.STEAM_LIBRARIES)
        found_set = set(found)

        # Remove paths that no longer exist on disk
        dead = {p for p in saved if not Path(p).exists()}

        # Add paths Steam knows about that we don't have -- only if they exist on disk
        # (Steam keeps dead paths in libraryfolders.vdf until manually removed)
        added = {p for p in found_set - saved if Path(p).exists()}

        if not dead and not added:
            return

        # Apply changes
        out = [p for p in self.STEAM_LIBRARIES if p not in dead]
        for p in sorted(added):
            if p not in out:
                out.append(p)

        if dead:
            logger.info(
                t("logs.config.removed_dead_libraries", count=len(dead)),
            )
            for p in sorted(dead):
                logger.info("  Removed: %s" % p)

        if added:
            logger.info(
                t("logs.config.added_new_libraries", count=len(added)),
            )
            for p in sorted(added):
                logger.info("  Added: %s" % p)

        self.STEAM_LIBRARIES = out
        self.save()

    def _detect_library_folders(self) -> list[str]:
        # parse libraryfolders.vdf for library paths
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

            logger.info(t("logs.config.library_folders_detected", count=len(libraries)))

        except Exception as e:
            logger.error(t("logs.config.library_read_error", error=e))

        return list(libraries)

    def get_detected_user(self) -> tuple[str | None, str | None]:
        # find steam user from userdata folder
        if not self.STEAM_PATH:
            return None, None

        userdata = self.STEAM_PATH / "userdata"
        if not userdata.exists():
            return None, None

        # Find first valid user directory
        for item in userdata.iterdir():
            if item.is_dir() and item.name.isdigit():
                if (item / "config" / "localconfig.vdf").exists():
                    account_id = int(item.name)
                    steam_id_64 = str(account_id + 76561197960265728)
                    logger.debug("Detected Steam user: %d" % account_id)
                    return str(account_id), steam_id_64

        return None, None

    def get_localconfig_path(self, account_id: str) -> Path | None:
        if not self.STEAM_PATH or not account_id:
            return None
        return self.STEAM_PATH / "userdata" / account_id / "config" / "localconfig.vdf"


# Global instance
config = Config()
