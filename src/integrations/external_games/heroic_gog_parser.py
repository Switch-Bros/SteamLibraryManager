"""Parser for GOG games installed via Heroic Games Launcher.

Reads Heroic's gog_store/installed.json to detect GOG titles.
Note: GOG format uses an 'installed' array wrapper and may lack
a 'title' field, requiring name resolution from install_path or metadata.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from src.integrations.external_games.base_parser import BaseExternalParser
from src.integrations.external_games.models import ExternalGame

__all__ = ["HeroicGOGParser"]

logger = logging.getLogger("steamlibmgr.external_games.heroic_gog")

_NATIVE = Path.home() / ".config" / "heroic" / "gog_store" / "installed.json"
_FLATPAK = (
    Path.home() / ".var" / "app" / "com.heroicgameslauncher.hgl" / "config" / "heroic" / "gog_store" / "installed.json"
)

# Pattern for human-readable size strings like "27.8 MiB", "1.2 GiB"
_SIZE_PATTERN = re.compile(r"([\d.]+)\s*(B|KiB|MiB|GiB|TiB|KB|MB|GB|TB)", re.IGNORECASE)
_SIZE_MULTIPLIERS: dict[str, int] = {
    "b": 1,
    "kb": 1000,
    "kib": 1024,
    "mb": 1000**2,
    "mib": 1024**2,
    "gb": 1000**3,
    "gib": 1024**3,
    "tb": 1000**4,
    "tib": 1024**4,
}


def _parse_size_string(size_str: str) -> int:
    """Parse human-readable size string to bytes.

    Args:
        size_str: Size like "27.8 MiB" or "1.2 GiB".

    Returns:
        Size in bytes, 0 if unparseable.
    """
    match = _SIZE_PATTERN.match(size_str.strip())
    if not match:
        return 0
    value = float(match.group(1))
    unit = match.group(2).lower()
    return int(value * _SIZE_MULTIPLIERS.get(unit, 1))


class HeroicGOGParser(BaseExternalParser):
    """Parser for GOG games installed through Heroic."""

    def platform_name(self) -> str:
        """Return platform name.

        Returns:
            Platform identifier.
        """
        return "Heroic (GOG)"

    def is_available(self) -> bool:
        """Check if Heroic GOG config exists.

        Returns:
            True if installed.json is found.
        """
        return self._find_config_file() is not None

    def get_config_paths(self) -> list[Path]:
        """Return native and Flatpak config paths.

        Returns:
            List of possible installed.json paths.
        """
        return [_NATIVE, _FLATPAK]

    def read_games(self) -> list[ExternalGame]:
        """Read installed GOG games from Heroic's config.

        Returns:
            List of detected GOG games.
        """
        config_path = self._find_config_file()
        if not config_path:
            return []

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to read Heroic GOG config: %s", e)
            return []

        installed = data.get("installed", []) if isinstance(data, dict) else []
        if not isinstance(installed, list):
            return []

        is_flatpak = str(config_path).startswith(str(Path.home() / ".var"))
        heroic_config = config_path.parent.parent
        games: list[ExternalGame] = []

        for entry in installed:
            if not isinstance(entry, dict):
                continue
            if entry.get("is_dlc", False):
                continue

            app_name = entry.get("appName", "")
            install_path = entry.get("install_path", "")
            name = self._resolve_name(app_name, install_path, heroic_config)

            size_raw = entry.get("install_size", 0)
            install_size = _parse_size_string(str(size_raw)) if isinstance(size_raw, str) else int(size_raw or 0)

            launch_cmd = self._build_launch_command(app_name, is_flatpak)
            metadata: list[tuple[str, str]] = []
            if entry.get("version"):
                metadata.append(("version", str(entry["version"])))
            if entry.get("language"):
                metadata.append(("language", str(entry["language"])))

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=app_name,
                    name=name,
                    install_path=Path(install_path) if install_path else None,
                    launch_command=launch_cmd,
                    install_size=install_size,
                    platform_metadata=tuple(metadata),
                )
            )

        logger.info("Found %d GOG games via Heroic", len(games))
        return games

    @staticmethod
    def _resolve_name(app_name: str, install_path: str, heroic_config: Path) -> str:
        """Resolve game name from metadata or install path.

        GOG installed.json lacks a title field. Try metadata cache
        first, then fall back to the last component of install_path.

        Args:
            app_name: GOG app ID.
            install_path: Installation directory.
            heroic_config: Path to heroic config root.

        Returns:
            Resolved game name.
        """
        # Try store_cache metadata
        cache_file = heroic_config / "store_cache" / f"{app_name}.json"
        if cache_file.exists():
            try:
                meta = json.loads(cache_file.read_text(encoding="utf-8"))
                if isinstance(meta, dict) and meta.get("title"):
                    return str(meta["title"])
            except (OSError, json.JSONDecodeError):
                pass

        # Fall back to install path last component
        if install_path:
            return Path(install_path).name

        return app_name

    @staticmethod
    def _build_launch_command(app_name: str, is_flatpak: bool) -> str:
        """Build the Heroic launch URI for a GOG game.

        Args:
            app_name: GOG app ID.
            is_flatpak: Whether Heroic is installed as Flatpak.

        Returns:
            Launch command string.
        """
        uri = f"heroic://launch/{app_name}?runner=gog"
        if is_flatpak:
            return f'flatpak run com.heroicgameslauncher.hgl --no-gui --no-sandbox "{uri}"'
        return uri
