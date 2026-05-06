#
# steam_library_manager/integrations/external_games/emulator_parsers/protocol.py
# Protocol + dataclasses for emulator config parsers
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = [
    "EmulatorConfigParser",
    "GameRef",
    "InstalledEmulator",
]


@dataclass(frozen=True)
class GameRef:
    """ROM reference from an emulator's own library cache."""

    name: str
    path: Path
    system: str


@dataclass(frozen=True)
class InstalledEmulator:
    """Detected emulator + its discovered game dirs."""

    name: str
    systems: tuple[str, ...]
    executable: Path
    source: str  # "flatpak", "system", "appimage", "user_override"
    game_dirs: tuple[Path, ...]


@runtime_checkable
class EmulatorConfigParser(Protocol):
    """Interface for emulator-specific config parsers.

    Each parser implements this for ONE emulator. Parsers are stateless and
    accept optional `config_path` overrides for testability.
    """

    @property
    def name(self) -> str:
        """Human-readable emulator name (e.g. 'Eden', 'Ryujinx')."""
        ...

    @property
    def systems(self) -> tuple[str, ...]:
        """System IDs this emulator supports (e.g. ('switch',))."""
        ...

    def is_installed(self) -> bool:
        """True if the emulator binary is found anywhere we look."""
        ...

    def get_executable(self) -> Path | None:
        """Path to a launchable executable (flatpak sentinel, system bin, AppImage)."""
        ...

    def get_game_dirs(self) -> list[Path]:
        """Game directories read from the emulator's own config files."""
        ...

    def get_known_games(self) -> list[GameRef]:
        """Pre-cached game list from the emulator (e.g. RetroArch playlists). Optional."""
        ...
