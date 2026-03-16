#
# steam_library_manager/core/shortcuts_manager.py
# CRUD for non-Steam game shortcuts in shortcuts.vdf
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zlib import crc32

from steam_library_manager.core import vdf_parser

__all__ = [
    "ShortcutsManager",
    "SteamShortcut",
    "generate_app_id",
    "generate_preliminary_id",
    "generate_short_app_id",
    "generate_shortcut_id",
]

logger = logging.getLogger("steamlibmgr.shortcuts")

_MAX_BACKUPS = 5


def generate_preliminary_id(exe: str, appname: str) -> int:
    """Generate 64-bit preliminary Steam ID for a non-Steam game."""
    key = (exe + appname).encode("utf-8")
    top = crc32(key) & 0xFFFFFFFF | 0x80000000
    return (top << 32) | 0x02000000


def generate_app_id(exe: str, appname: str) -> str:
    """Big Picture grid image ID as string."""
    return str(generate_preliminary_id(exe, appname))


def generate_short_app_id(exe: str, appname: str) -> str:
    """Standard grid/hero/logo image ID as string."""
    return str(generate_preliminary_id(exe, appname) >> 32)


def generate_shortcut_id(exe: str, appname: str) -> int:
    """Signed 32-bit appid for the shortcuts.vdf entry."""
    return (generate_preliminary_id(exe, appname) >> 32) - 0x100000000


@dataclass
class SteamShortcut:
    """Non-Steam game shortcut entry for shortcuts.vdf."""

    appid: int
    app_name: str
    exe: str
    start_dir: str
    icon: str = ""
    shortcut_path: str = ""
    launch_options: str = ""
    is_hidden: bool = False
    allow_desktop_config: bool = True
    allow_overlay: bool = True
    open_vr: bool = False
    devkit: bool = False
    devkit_game_id: str = ""
    devkit_override_app_id: int = 0
    last_play_time: int = 0
    flatpak_app_id: str = ""
    sort_as: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    def to_vdf_dict(self) -> dict[str, object]:
        """Convert to shortcuts.vdf binary format dict."""
        return {
            "appid": self.appid,
            "appname": self.app_name,
            "exe": self.exe,
            "StartDir": self.start_dir,
            "icon": self.icon,
            "ShortcutPath": self.shortcut_path,
            "LaunchOptions": self.launch_options,
            "IsHidden": int(self.is_hidden),
            "AllowDesktopConfig": int(self.allow_desktop_config),
            "AllowOverlay": int(self.allow_overlay),
            "OpenVR": int(self.open_vr),
            "Devkit": int(self.devkit),
            "DevkitGameID": self.devkit_game_id,
            "DevkitOverrideAppID": self.devkit_override_app_id,
            "LastPlayTime": self.last_play_time,
            "FlatpakAppID": self.flatpak_app_id,
            "sortas": self.sort_as,
            "tags": dict(self.tags),
        }

    @classmethod
    def from_vdf_dict(cls, data: dict[str, Any]) -> SteamShortcut:
        """Create from a VDF dictionary (handles mixed-case keys)."""
        return cls(
            appid=int(data.get("appid", 0)),
            app_name=str(data.get("appname", "")),
            exe=str(data.get("exe", "")),
            start_dir=str(data.get("StartDir", data.get("startdir", ""))),
            icon=str(data.get("icon", "")),
            shortcut_path=str(data.get("ShortcutPath", data.get("shortcutpath", ""))),
            launch_options=str(data.get("LaunchOptions", data.get("launchoptions", ""))),
            is_hidden=bool(data.get("IsHidden", data.get("ishidden", 0))),
            allow_desktop_config=bool(data.get("AllowDesktopConfig", data.get("allowdesktopconfig", 1))),
            allow_overlay=bool(data.get("AllowOverlay", data.get("allowoverlay", 1))),
            open_vr=bool(data.get("OpenVR", data.get("openvr", 0))),
            devkit=bool(data.get("Devkit", data.get("devkit", 0))),
            devkit_game_id=str(data.get("DevkitGameID", data.get("devkitgameid", ""))),
            devkit_override_app_id=int(data.get("DevkitOverrideAppID", data.get("devkitoverrideappid", 0))),
            last_play_time=int(data.get("LastPlayTime", data.get("lastplaytime", 0))),
            flatpak_app_id=str(data.get("FlatpakAppID", data.get("flatpakappid", ""))),
            sort_as=str(data.get("sortas", "")),
            tags=dict(data.get("tags", {})),
        )


class ShortcutsManager:
    """CRUD for non-Steam game shortcuts with backup and dedup."""

    def __init__(self, steam_userdata_path: Path, account_id: str) -> None:
        self._userdata = steam_userdata_path
        self._account_id = account_id

    def get_shortcuts_path(self) -> Path:
        return self._userdata / self._account_id / "config" / "shortcuts.vdf"

    def read_shortcuts(self) -> list[SteamShortcut]:
        """Read all shortcuts from shortcuts.vdf (empty list if missing)."""
        path = self.get_shortcuts_path()
        if not path.exists():
            return []

        try:
            data = path.read_bytes()
            parsed = vdf_parser.binary_loads(data)
            shortcuts_dict = parsed.get("shortcuts", {})
            if not isinstance(shortcuts_dict, dict):
                return []
            return [SteamShortcut.from_vdf_dict(entry) for entry in shortcuts_dict.values() if isinstance(entry, dict)]
        except (OSError, ValueError) as e:
            logger.error("Failed to read shortcuts.vdf: %s", e)
            return []

    def write_shortcuts(self, shortcuts: list[SteamShortcut]) -> None:
        """Write shortcuts to shortcuts.vdf (creates backup first)."""
        path = self.get_shortcuts_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            self._create_backup(path)

        vdf_dict: dict[str, object] = {
            "shortcuts": {str(i): s.to_vdf_dict() for i, s in enumerate(shortcuts)},
        }
        data = vdf_parser.binary_dumps(vdf_dict)
        path.write_bytes(data)
        logger.info("Wrote %d shortcuts to %s", len(shortcuts), path)

    def add_shortcut(self, shortcut: SteamShortcut) -> bool:
        """Add a shortcut if not duplicate. Returns True if added."""
        if self.has_shortcut(shortcut.app_name):
            logger.debug("Shortcut already exists: %s", shortcut.app_name)
            return False

        shortcuts = self.read_shortcuts()
        shortcuts.append(shortcut)
        self.write_shortcuts(shortcuts)
        return True

    def remove_shortcut(self, app_name: str) -> bool:
        """Remove shortcut by name. Returns True if found and removed."""
        shortcuts = self.read_shortcuts()
        lower_name = app_name.lower()
        new_shortcuts = [s for s in shortcuts if s.app_name.lower() != lower_name]

        if len(new_shortcuts) == len(shortcuts):
            return False

        self.write_shortcuts(new_shortcuts)
        return True

    def has_shortcut(self, app_name: str) -> bool:
        """Case-insensitive check whether a shortcut exists."""
        lower_name = app_name.lower()
        return any(s.app_name.lower() == lower_name for s in self.read_shortcuts())

    def get_grid_paths(self, exe: str, app_name: str) -> dict[str, Path]:
        """Grid image paths (cover, header, hero, logo, big_picture)."""
        short_id = generate_short_app_id(exe, app_name)
        big_id = generate_app_id(exe, app_name)
        grid_dir = self._userdata / self._account_id / "config" / "grid"

        return {
            "cover": grid_dir / f"{short_id}p.jpg",
            "header": grid_dir / f"{short_id}.jpg",
            "hero": grid_dir / f"{short_id}_hero.jpg",
            "logo": grid_dir / f"{short_id}_logo.png",
            "big_picture": grid_dir / f"{big_id}.jpg",
        }

    def _create_backup(self, path: Path) -> None:
        timestamp = int(time.time())
        backup = path.with_name(f"{path.name}.bak.{timestamp}")
        try:
            backup.write_bytes(path.read_bytes())
            logger.debug("Created backup: %s", backup)
        except OSError as e:
            logger.warning("Failed to create backup: %s", e)
            return

        backups = sorted(path.parent.glob(f"{path.name}.bak.*"), reverse=True)
        for old in backups[_MAX_BACKUPS:]:
            try:
                old.unlink()
            except OSError:
                pass
