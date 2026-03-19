#
# steam_library_manager/integrations/external_games/rom_parser.py
# ROM file scanner for emulator-based game detection
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

from steam_library_manager.integrations.external_games.base_parser import BaseExternalParser
from steam_library_manager.integrations.external_games.emulator_config import (
    EMUDECK_ROM_DIRS,
    EMULATORS,
    ROM_SEARCH_PATHS,
    SYSTEM_EMULATORS,
    EmulatorDef,
)
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["RomParser"]

logger = logging.getLogger("steamlibmgr.external_games.rom_parser")

# regex patterns for stripping ROM junk (IDs, versions, regions)
_RE_TITLE_ID = re.compile(r"\s*\[[0-9A-Fa-f]{16}]")
_RE_VER_BRACKET = re.compile(r"\s*\[v\d+]")
_RE_VER_PAREN = re.compile(r"\s*\(v[\d.]+\)")
_RE_REGION = re.compile(r"\s*\((USA|Europe|Japan|World|En|De|Fr|Es|It|Ko|Zh)\)")
_RE_TAGS = re.compile(r"\s*\((DLC|Update|NSP|XCI|CIA|Demo)\)", re.IGNORECASE)
_RE_TRAIL_BRACKET = re.compile(r"\s*\[.*?]\s*$")
_RE_TRAIL_PAREN = re.compile(r"\s*\(.*?\)\s*$")


class RomParser(BaseExternalParser):
    """Scan ROM directories and pair with detected emulators."""

    # maps alt dir names to canonical IDs (e.g. gbc -> gb)
    _SYSTEM_ALIASES = {
        "gbc": "gb",
    }

    APPIMAGE_DIRS = (
        "~/.local/share/applications",
        "~/Applications",
        "~/apps",
        "~/AppImages",
        "/mnt/volume/Emulation/tools",
        "~/Emulation/tools",
        "~/Downloads",
    )

    EMUDECK_LAUNCHER_DIRS = (
        "/mnt/volume/Emulation/tools/launchers",
        "~/Emulation/tools/launchers",
    )

    def platform_name(self):
        return "Emulation (ROMs)"

    def is_available(self):
        # true if at least one ROM dir exists with files
        for p in ROM_SEARCH_PATHS:
            path = Path(p).expanduser()
            if not path.is_dir():
                continue
            try:
                if any(path.iterdir()):
                    return True
            except PermissionError:
                continue
        return False

    def get_config_paths(self):
        # collect existing ROM base dirs
        return [Path(p).expanduser() for p in ROM_SEARCH_PATHS if Path(p).expanduser().is_dir()]

    def read_games(self):
        # scan ROMs and match to emulators
        emus = self._detect_emulators()
        if not emus:
            logger.info("No emulators detected")
            return []

        rom_dirs = self._find_rom_directories()
        if not rom_dirs:
            logger.info("No ROM directories found")
            return []

        games = []
        for d, sys_name in rom_dirs:
            matches = self._get_emulators_for_system(sys_name, emus)
            if not matches:
                logger.debug("No emulator for: %s" % sys_name)
                continue

            emu, exe = matches[0]  # first = highest priority
            roms = self._scan_rom_files(d, emu.extensions)

            for rp in roms:
                name = self._extract_game_name(rp)
                cmd = self._build_launch_command(emu, exe, rp)
                games.append(
                    ExternalGame(
                        platform="Emulation (%s)" % emu.system_display,
                        platform_app_id="rom:%s:%s" % (sys_name, rp.name),
                        name=name,
                        install_path=rp.parent,
                        executable=str(exe),
                        launch_command=cmd,
                        platform_metadata=(
                            ("emulator", emu.name),
                            ("system", sys_name),
                            ("rom_file", rp.name),
                            ("rom_extension", rp.suffix.lower()),
                        ),
                    )
                )

        logger.info("Found %d ROMs across %d systems" % (len(games), len(rom_dirs)))
        return games

    def _detect_emulators(self):
        # probe each emulator in EMULATORS list
        found = {}
        for e in EMULATORS:
            if e.name in found:
                continue
            p = self._find_emulator(e)
            if p:
                found[e.name] = p
                logger.debug("Found %s at %s" % (e.name, p))
        return found

    def _find_emulator(self, emu: EmulatorDef) -> Path | None:
        # locate emulator: EmuDeck -> flatpak -> PATH -> AppImage

        # EmuDeck launchers first
        if emu.emudeck_launcher:
            for ld in self.EMUDECK_LAUNCHER_DIRS:
                lp = Path(ld).expanduser() / emu.emudeck_launcher
                if lp.is_file() and lp.stat().st_mode & 0o111:
                    return lp

        # flatpak sentinel
        if emu.flatpak_id and shutil.which("flatpak"):
            try:
                r = subprocess.run(
                    ["flatpak", "info", emu.flatpak_id],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if r.returncode == 0:
                    return Path("/flatpak/%s" % emu.flatpak_id)
            except (subprocess.TimeoutExpired, OSError):
                pass

        # system PATH (no globs)
        for pat in emu.exe_patterns:
            if "*" not in pat:
                f = shutil.which(pat)
                if f:
                    return Path(f)

        # AppImage in common dirs
        for d_str in self.APPIMAGE_DIRS:
            sd = Path(d_str).expanduser()
            if not sd.is_dir():
                continue
            for pat in emu.exe_patterns:
                if "*" in pat:
                    m = sorted(sd.glob(pat), reverse=True)
                    if m:
                        return m[0]
                else:
                    ex = sd / pat
                    if ex.is_file():
                        return ex

        return None

    @staticmethod
    def _find_rom_directories():
        # locate non-empty ROM directories
        found = []

        for b_str in ROM_SEARCH_PATHS:
            b = Path(b_str).expanduser()
            if not b.is_dir():
                continue
            for sys_name, d_name in EMUDECK_ROM_DIRS.items():
                sd = b / d_name
                if not sd.is_dir():
                    continue
                try:
                    if any(sd.iterdir()):
                        found.append((sd, sys_name))
                except PermissionError:
                    continue

        # deduplicate by resolved path
        seen = set()
        uniq = []
        for p, n in found:
            try:
                k = str(p.resolve())
            except OSError:
                k = str(p)
            if k not in seen:
                seen.add(k)
                uniq.append((p, n))
        return uniq

    @staticmethod
    def _get_emulators_for_system(sys_name, detected):
        # match system to available emulators (resolves aliases)
        eff = RomParser._SYSTEM_ALIASES.get(sys_name, sys_name)
        return [(e, detected[e.name]) for e in SYSTEM_EMULATORS.get(eff, []) if e.name in detected]

    @staticmethod
    def _scan_rom_files(d, exts):
        # non-recursive scan for ROMs
        roms = []
        try:
            for entry in d.iterdir():
                if entry.is_file() and entry.suffix.lower() in exts:
                    roms.append(entry)
        except PermissionError:
            logger.warning("Cannot read: %s" % d)
        return sorted(roms, key=lambda p: p.name.lower())

    @staticmethod
    def _extract_game_name(rp):
        # strip junk from ROM filename
        name = rp.stem
        # strip: title IDs, versions, regions, tags, leftovers
        for pat in (
            _RE_TITLE_ID,
            _RE_VER_BRACKET,
            _RE_VER_PAREN,
            _RE_REGION,
            _RE_TAGS,
            _RE_TRAIL_BRACKET,
            _RE_TRAIL_PAREN,
        ):
            name = pat.sub("", name)
        name = name.strip(" -_.")
        return name if name else rp.stem

    @staticmethod
    def _build_launch_command(emu, exe, rp):
        # assemble launch command
        es = str(exe)

        # flatpak sentinel
        if es.startswith("/flatpak/"):
            fid = exe.name
            parts = emu.launch_template.split('"{exe}"')
            if len(parts) == 2:
                args = parts[1].format(rom=str(rp))
                return "flatpak run %s%s" % (fid, args)
            return 'flatpak run %s "%s"' % (fid, rp)

        return emu.launch_template.format(exe=es, rom=str(rp))
