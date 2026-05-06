#
# steam_library_manager/integrations/external_games/emulator_parsers/emudeck_hint.py
# EmuDeck settings hint provider - fallback for emulators without their own library config
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_config import EMUDECK_ROM_DIRS

__all__ = ["EmuDeckHintProvider"]

logger = logging.getLogger("steamlibmgr.emulator_parsers.emudeck_hint")


class EmuDeckHintProvider:
    """Reads EmuDeck's settings.sh and derives ROM directories.

    EmuDeck has a known concatenation bug: the `romsPath` value contains
    duplicated path segments. We work around that by reading `emulationPath`
    and constructing `<emulationPath>/roms/<system>` ourselves.
    """

    _DEFAULT_SETTINGS_PATHS: tuple[Path, ...] = (
        Path.home() / "emudeck" / "settings.sh",
        Path.home() / ".config" / "EmuDeck" / "backend" / "settings.sh",
    )

    def __init__(self, settings_paths: tuple[Path, ...] | None = None) -> None:
        self._settings_paths = settings_paths if settings_paths is not None else self._DEFAULT_SETTINGS_PATHS

    def is_available(self) -> bool:
        return any(sp.is_file() for sp in self._settings_paths)

    def get_emulation_path(self) -> Path | None:
        # EmuDeck has a known concat bug like:
        #   emulationPath="/mnt/games/Emulation"/Emulation
        # The literal bash-evaluated value would be "/mnt/games/Emulation/Emulation",
        # which does not exist. So we try several candidate parsings and return the
        # first one that actually points to an existing directory.
        for sp in self._settings_paths:
            if not sp.is_file():
                continue
            try:
                with open(sp, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line.startswith("emulationPath="):
                            continue
                        rhs = line.split("=", 1)[1]
                        for cand in _candidate_values(rhs):
                            p = Path(cand).expanduser()
                            if p.is_dir():
                                return p
            except OSError as exc:
                logger.warning("could not read %s: %s" % (sp, exc))
                continue
        return None

    def get_rom_dir(self, system: str) -> Path | None:
        base = self.get_emulation_path()
        if not base:
            return None
        subdir = EMUDECK_ROM_DIRS.get(system)
        if not subdir:
            return None
        rom_dir = base / "roms" / subdir
        return rom_dir if rom_dir.is_dir() else None

    def get_all_rom_dirs(self) -> dict[str, Path]:
        # convenience: returns {system_id: existing_rom_dir} for every known system
        out: dict[str, Path] = {}
        for sys_id in EMUDECK_ROM_DIRS:
            d = self.get_rom_dir(sys_id)
            if d is not None:
                out[sys_id] = d
        return out

    def get_tools_path(self) -> Path | None:
        # EmuDeck stores launcher scripts under <emulationPath>/tools/launchers
        base = self.get_emulation_path()
        if not base:
            return None
        tools = base / "tools"
        return tools if tools.is_dir() else None


def _candidate_values(rhs: str) -> list[str]:
    """Generate candidate path values from an EmuDeck shell-style RHS.

    The EmuDeck concat bug means the bash-evaluated value (concatenated parts)
    is often invalid, while the contents of the first quoted segment are usually
    correct. We try several interpretations and the caller picks the first
    existing directory.
    """
    rhs = rhs.strip()
    candidates: list[str] = []

    # 1) bash-evaluated form: strip leading/trailing quotes, drop internal quotes
    bash_eval = rhs.replace('"', "").replace("'", "").strip()
    if bash_eval:
        candidates.append(bash_eval)

    # 2) extract content of the first quoted segment ("..." or '...')
    for q in ('"', "'"):
        if rhs.count(q) >= 2:
            start = rhs.find(q)
            end = rhs.find(q, start + 1)
            if end > start:
                quoted = rhs[start + 1 : end]
                if quoted and quoted not in candidates:
                    candidates.append(quoted)

    # 3) raw RHS (in case there are no quotes at all)
    if rhs and rhs not in candidates:
        candidates.append(rhs)

    return candidates
