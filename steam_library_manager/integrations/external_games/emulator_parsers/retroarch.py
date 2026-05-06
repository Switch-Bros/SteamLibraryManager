#
# steam_library_manager/integrations/external_games/emulator_parsers/retroarch.py
# RetroArch parser - reads cached game library from playlist .lpl files
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_parsers._base import BaseEmulatorParser
from steam_library_manager.integrations.external_games.emulator_parsers.protocol import GameRef

__all__ = ["RetroArchParser"]

logger = logging.getLogger("steamlibmgr.emulator_parsers.retroarch")

# RetroArch playlist filename -> SLM system ID
# (RetroArch uses long descriptive names, we map them to our short IDs)
_PLAYLIST_TO_SYSTEM = {
    "Nintendo - Nintendo Entertainment System": "nes",
    "Nintendo - Super Nintendo Entertainment System": "snes",
    "Nintendo - Game Boy": "gb",
    "Nintendo - Game Boy Color": "gb",
    "Nintendo - Game Boy Advance": "gba",
    "Nintendo - Nintendo 64": "n64",
    "Nintendo - Nintendo DS": "nds",
    "Nintendo - Nintendo 3DS": "3ds",
    "Nintendo - GameCube": "gc",
    "Nintendo - Wii": "wii",
    "Nintendo - Wii U": "wiiu",
    "Nintendo - Switch": "switch",
    "Sega - Master System - Mark III": "sms",
    "Sega - Mega Drive - Genesis": "genesis",
    "Sega - Saturn": "saturn",
    "Sega - Dreamcast": "dreamcast",
    "Sony - PlayStation": "psx",
    "Sony - PlayStation 2": "ps2",
    "Sony - PlayStation Portable": "psp",
    "Atari - 2600": "atari2600",
    "DOS": "dos",
    "Arcade": "arcade",
}


class RetroArchParser(BaseEmulatorParser):
    """RetroArch - multi-system emulator. Returns games from playlist .lpl files."""

    EMULATOR_NAME = "RetroArch"
    EMULATOR_SYSTEMS = (
        "nes",
        "snes",
        "gb",
        "gba",
        "n64",
        "nds",
        "3ds",
        "gc",
        "wii",
        "wiiu",
        "switch",
        "sms",
        "genesis",
        "saturn",
        "dreamcast",
        "psx",
        "ps2",
        "psp",
        "atari2600",
        "dos",
        "arcade",
    )
    FLATPAK_ID = "org.libretro.RetroArch"
    SYSTEM_BIN_NAMES = ("retroarch", "RetroArch")
    NATIVE_CONFIG_REL = ("retroarch",)
    FLATPAK_CONFIG_REL = ("retroarch",)

    def __init__(self, playlists_dir: Path | None = None) -> None:
        self._playlists_override = playlists_dir

    def get_game_dirs(self) -> list[Path]:
        # RetroArch's "library" lives in playlists, not in scanned dirs.
        # We expose game_dirs as the unique parent dirs of all known ROMs so the
        # service can still treat them like directories for user-add purposes.
        seen: set[Path] = set()
        for ref in self.get_known_games():
            seen.add(ref.path.parent)
        return sorted(seen)

    def get_known_games(self) -> list[GameRef]:
        games: list[GameRef] = []
        for pl in self._iter_playlist_files():
            system = _PLAYLIST_TO_SYSTEM.get(pl.stem, "")
            if not system:
                # unknown playlist; skip rather than guess wrong system
                continue
            games.extend(self._parse_playlist(pl, system))
        return games

    # ---- helpers ----

    def _iter_playlist_files(self):
        if self._playlists_override is not None:
            base = self._playlists_override
            if base.is_dir():
                for f in sorted(base.glob("*.lpl")):
                    yield f
            return

        home = Path.home()
        candidates = (
            home / ".var" / "app" / self.FLATPAK_ID / "config" / "retroarch" / "playlists",
            home / ".config" / "retroarch" / "playlists",
        )
        for base in candidates:
            if not base.is_dir():
                continue
            for f in sorted(base.glob("*.lpl")):
                yield f

    @staticmethod
    def _parse_playlist(playlist_file: Path, system: str) -> list[GameRef]:
        try:
            with open(playlist_file, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            logger.warning("could not read %s: %s" % (playlist_file, exc))
            return []

        items = data.get("items", []) if isinstance(data, dict) else []
        if not isinstance(items, list):
            return []

        results: list[GameRef] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            path = it.get("path", "")
            label = it.get("label", "") or Path(path).stem if path else ""
            if not path:
                continue
            results.append(GameRef(name=label, path=Path(path), system=system))
        return results
