#
# steam_library_manager/integrations/external_games/models.py
# Data models and platform constants for external (non-Steam) games
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeAlias

from steam_library_manager.utils.i18n import t

__all__ = [
    "ExternalGame",
    "PlatformName",
    "SUPPORTED_PLATFORMS",
    "get_collection_emoji",
]

PlatformName: TypeAlias = str


@dataclass(frozen=True)
class ExternalGame:
    """Game detected from an external (non-Steam) platform."""

    platform: PlatformName
    platform_app_id: str
    name: str
    install_path: Path | None = None
    executable: str | None = None
    launch_command: str = ""
    icon_path: Path | None = None
    install_size: int = 0
    is_installed: bool = True
    platform_metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)


SUPPORTED_PLATFORMS: tuple[str, ...] = (
    "Heroic (Epic)",
    "Heroic (GOG)",
    "Heroic (Amazon)",
    "Lutris",
    "itch.io",
    "Bottles",
    "Flatpak",
    "Emulation (ROMs)",
)


# Mapping: Collection-Name -> emoji.json Key (NOT the emoji itself!)
# t() is called lazily in get_collection_emoji() — NOT at import time!
_COLLECTION_EMOJI_KEYS: dict[str, str] = {
    # Platform parsers (Phase 6.5)
    "Epic Games": "emoji.epic",
    "GOG Galaxy": "emoji.gog",
    "Amazon Games": "emoji.amazon",
    "Lutris": "emoji.game",
    "Bottles": "emoji.bottles",
    "itch.io": "emoji.dice",
    "Flatpak": "emoji.flatpak",
    "Heroic": "emoji.heroic",
    "EA": "emoji.ea",
    "Ubisoft": "emoji.ubisoft",
    # ROM systems (Phase 6.5.2)
    "Nintendo Switch": "emoji.switch",
    "Nintendo Wii U": "emoji.wiiu",
    "Nintendo Wii": "emoji.wii",
    "Nintendo 3DS": "emoji.3ds",
    "Nintendo DS": "emoji.ds",
    "Game Boy Advance": "emoji.gba",
    "Game Boy": "emoji.gameboy",
    "Super Nintendo": "emoji.snes",
    "Nintendo Entertainment System": "emoji.nes",
    "Nintendo 64": "emoji.n64",
    "Nintendo GameCube": "emoji.gamecube",
    "PlayStation Portable": "emoji.psp",
    "MS-DOS": "emoji.msdos",
}


def get_collection_emoji(collection_name: str) -> str:
    """Get emoji for an external platform/system collection.

    Called at runtime (not import time) to ensure i18n is initialized.
    """
    key = _COLLECTION_EMOJI_KEYS.get(collection_name, "")
    return t(key) if key else ""
