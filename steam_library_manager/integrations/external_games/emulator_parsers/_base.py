#
# steam_library_manager/integrations/external_games/emulator_parsers/_base.py
# Shared helpers for emulator config parsers
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_parsers.protocol import (
    GameRef,
    InstalledEmulator,
)

__all__ = ["BaseEmulatorParser"]

logger = logging.getLogger("steamlibmgr.emulator_parsers.base")


class BaseEmulatorParser:
    """Common helpers for parser implementations.

    Subclasses set class attributes for emulator metadata and override the
    config reading methods. Discovery of the executable is handled here.
    """

    # Subclass overrides (class-level metadata):
    EMULATOR_NAME: str = ""
    EMULATOR_SYSTEMS: tuple[str, ...] = ()
    FLATPAK_ID: str = ""
    SYSTEM_BIN_NAMES: tuple[str, ...] = ()  # e.g. ("eden", "Eden.AppImage")
    NATIVE_CONFIG_REL: tuple[str, ...] = ()  # paths relative to ~/.config or ~
    FLATPAK_CONFIG_REL: tuple[str, ...] = ()  # paths inside ~/.var/app/<id>/

    # ---- Protocol surface ----

    @property
    def name(self) -> str:
        return self.EMULATOR_NAME

    @property
    def systems(self) -> tuple[str, ...]:
        return self.EMULATOR_SYSTEMS

    def is_installed(self) -> bool:
        # An emulator counts as installed if we can find an executable OR if a
        # config file exists - the latter means the user has run it before, so
        # it is on the system somewhere even if our binary detection misses
        # the AppImage location.
        if self.get_executable() is not None:
            return True
        for cfg in self.iter_config_paths():
            if cfg.is_file():
                return True
        return False

    def get_executable(self) -> Path | None:
        # priority: flatpak (EmuDeck/Steam Deck default) -> system PATH -> user AppImage dirs
        if self.FLATPAK_ID and self._flatpak_installed(self.FLATPAK_ID):
            return Path("/flatpak/%s" % self.FLATPAK_ID)
        for bin_name in self.SYSTEM_BIN_NAMES:
            if "*" in bin_name:
                continue
            found = shutil.which(bin_name)
            if found:
                return Path(found)
        # check standard Linux user AppImage locations (FHS / xdg convention)
        appimage = self._find_appimage()
        if appimage is not None:
            return appimage
        return None

    def _find_appimage(self) -> Path | None:
        # standard places where users park AppImages on Linux
        home = Path.home()
        search_dirs = (
            home / "Applications",
            home / "AppImages",
            home / "Apps",
            home / ".local" / "bin",
            home / "bin",
        )
        # try exact filename match first, then case-insensitive prefix match
        bin_lower = [b.lower() for b in self.SYSTEM_BIN_NAMES if "*" not in b]
        for d in search_dirs:
            if not d.is_dir():
                continue
            try:
                entries = sorted(d.iterdir(), reverse=True)  # newest-named first
            except OSError:
                continue
            for entry in entries:
                if not entry.is_file():
                    continue
                if entry.suffix.lower() != ".appimage":
                    continue
                stem_lower = entry.stem.lower()
                # exact match on the binary name (e.g. "Eden.AppImage")
                for bin_name in self.SYSTEM_BIN_NAMES:
                    if "*" in bin_name:
                        continue
                    if entry.name == bin_name:
                        return entry
                # prefix match (e.g. "Eden-Linux-1.2.3.AppImage" matches "eden")
                for bn in bin_lower:
                    if stem_lower == bn or stem_lower.startswith(bn + "-") or stem_lower.startswith(bn + "_"):
                        return entry
        return None

    def get_game_dirs(self) -> list[Path]:
        # default: read from config files; subclasses override _parse_config_file
        for cfg in self.iter_config_paths():
            if not cfg.is_file():
                continue
            try:
                dirs = self._parse_config_file(cfg)
            except Exception as exc:
                logger.warning("%s: failed to parse %s: %s" % (self.EMULATOR_NAME, cfg, exc))
                continue
            if dirs:
                return [Path(d).expanduser() for d in dirs if d]
        return []

    def get_known_games(self) -> list[GameRef]:
        return []

    # ---- helpers for subclasses ----

    def iter_config_paths(self):
        # yield all (flatpak first, native second) candidate config locations
        home = Path.home()
        if self.FLATPAK_ID and self.FLATPAK_CONFIG_REL:
            base = home / ".var" / "app" / self.FLATPAK_ID / "config"
            for rel in self.FLATPAK_CONFIG_REL:
                yield base / rel
        if self.NATIVE_CONFIG_REL:
            cfg_home = home / ".config"
            for rel in self.NATIVE_CONFIG_REL:
                yield cfg_home / rel

    def _parse_config_file(self, path: Path) -> list[str]:
        # subclasses override
        return []

    @staticmethod
    def _flatpak_installed(flatpak_id: str) -> bool:
        if not shutil.which("flatpak"):
            return False
        try:
            r = subprocess.run(
                ["flatpak", "info", flatpak_id],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return r.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def to_installed_emulator(self) -> InstalledEmulator | None:
        # convenience: build the InstalledEmulator dataclass
        exe = self.get_executable()
        if exe is None:
            return None
        if str(exe).startswith("/flatpak/"):
            source = "flatpak"
        elif "AppImage" in exe.name:
            source = "appimage"
        else:
            source = "system"
        return InstalledEmulator(
            name=self.EMULATOR_NAME,
            systems=self.EMULATOR_SYSTEMS,
            executable=exe,
            source=source,
            game_dirs=tuple(self.get_game_dirs()),
        )
