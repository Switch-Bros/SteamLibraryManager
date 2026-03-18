#
# steam_library_manager/core/steam_account.py
# Steam account data model
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from dataclasses import dataclass, field
from zlib import crc32
import logging
import time

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
_MAX_BACKUPS = 5  # TODO: make configurable?


def generate_preliminary_id(exe, appname):
    # steam uses crc32 of exe+name for the unique id
    key = (exe + appname).encode("utf-8")
    top = crc32(key) & 0xFFFFFFFF | 0x80000000
    return (top << 32) | 0x02000000


def generate_app_id(exe, appname):
    # big picture grid id
    return str(generate_preliminary_id(exe, appname))


def generate_short_app_id(exe, appname):
    return str(generate_preliminary_id(exe, appname) >> 32)


def generate_shortcut_id(exe, appname):
    # dunno why steam subtracts this but it does
    return (generate_preliminary_id(exe, appname) >> 32) - 0x100000000


@dataclass
class SteamShortcut:
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
    tags: dict = field(default_factory=dict)

    def to_vdf_dict(self):
        # convert for steam's binary format
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
    def from_vdf_dict(cls, data):
        # parse steam's weird mixed-case format
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
    """Manage non-Steam game shortcuts.

    CRUD for shortcuts.vdf with auto-backup and dedup.
    """

    def __init__(self, steam_userdata_path, account_id):
        self._ud = steam_userdata_path
        self._acc = account_id

    def get_shortcuts_path(self):
        return self._ud / self._acc / "config" / "shortcuts.vdf"

    def read_shortcuts(self):
        # load from vdf
        p = self.get_shortcuts_path()
        if not p.exists():
            return []
        try:
            raw = p.read_bytes()
            parsed = vdf_parser.binary_loads(raw)
            sd = parsed.get("shortcuts", {})
            if not isinstance(sd, dict):
                return []
            out = []
            for _idx, entry in sd.items():
                if isinstance(entry, dict):
                    out.append(SteamShortcut.from_vdf_dict(entry))
            return out
        except (OSError, ValueError) as e:
            logger.error("failed to read shortcuts: %s" % e)
            return []

    def write_shortcuts(self, shortcuts):
        p = self.get_shortcuts_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            self._bak(p)
        # build vdf dict
        vdf = {"shortcuts": {}}
        for i, s in enumerate(shortcuts):
            vdf["shortcuts"][str(i)] = s.to_vdf_dict()
        p.write_bytes(vdf_parser.binary_dumps(vdf))
        logger.info("wrote %d shortcuts" % len(shortcuts))

    def add_shortcut(self, sh):
        if self.has_shortcut(sh.app_name):
            logger.debug("duplicate: %s" % sh.app_name)
            return False
        sc = self.read_shortcuts()
        sc.append(sh)
        self.write_shortcuts(sc)
        return True

    def remove_shortcut(self, name):
        sc = self.read_shortcuts()
        nm = name.lower()
        new = [s for s in sc if s.app_name.lower() != nm]
        if len(new) == len(sc):
            return False
        self.write_shortcuts(new)
        return True

    def has_shortcut(self, name):
        nm = name.lower()
        for s in self.read_shortcuts():
            if s.app_name.lower() == nm:
                return True
        return False

    def get_grid_paths(self, exe, app_name):
        # get image paths for non-steam game
        sid = generate_short_app_id(exe, app_name)
        bid = generate_app_id(exe, app_name)
        gdir = self._ud / self._acc / "config" / "grid"

        return {
            "cover": gdir / ("%sp.jpg" % sid),
            "header": gdir / ("%s.jpg" % sid),
            "hero": gdir / ("%s_hero.jpg" % sid),
            "logo": gdir / ("%s_logo.png" % sid),
            "big_picture": gdir / ("%s.jpg" % bid),
        }

    def _bak(self, path):
        # backup before overwrite
        ts = int(time.time())
        bp = path.with_name("%s.bak.%d" % (path.name, ts))
        try:
            bp.write_bytes(path.read_bytes())
            logger.debug("backup: %s" % bp)
        except OSError as e:
            logger.warning("backup failed: %s" % e)
            return
        # prune old
        old = sorted(path.parent.glob("%s.bak.*" % path.name), reverse=True)
        for f in old[_MAX_BACKUPS:]:
            try:
                f.unlink()
            except OSError:
                pass
