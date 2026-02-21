"""Data models for external (non-Steam) games.

Defines the ExternalGame dataclass and supported platform constants
used by all platform parsers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeAlias

__all__ = [
    "ExternalGame",
    "PlatformName",
    "SUPPORTED_PLATFORMS",
]

PlatformName: TypeAlias = str


@dataclass(frozen=True)
class ExternalGame:
    """Game detected from an external (non-Steam) platform.

    Args:
        platform: Platform identifier (e.g. "Heroic (Epic)").
        platform_app_id: Platform-specific unique ID.
        name: Display name of the game.
        install_path: Installation directory.
        executable: Executable name or path.
        launch_command: Full launch command for Steam shortcut.
        icon_path: Path to icon file if available.
        install_size: Installation size in bytes.
        is_installed: Whether the game is currently installed.
        platform_metadata: Additional platform-specific key-value pairs.
            Uses tuple of tuples for frozen dataclass compatibility.
    """

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
)
