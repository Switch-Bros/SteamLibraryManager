#
# steam_library_manager/integrations/external_games/bottles_parser.py
# Detects programs from Bottles wine prefixes via bottle.yml and library.yml
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import os
from pathlib import Path

from steam_library_manager.integrations.external_games.base_parser import BaseExternalParser

try:
    import yaml

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["BottlesParser"]

logger = logging.getLogger("steamlibmgr.external_games.bottles")


def _get_bottles_base() -> Path:
    """Return the XDG-based Bottles data directory."""
    xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg) / "bottles"


_FLATPAK_BASE = Path.home() / ".var" / "app" / "com.usebottles.bottles" / "data" / "bottles"


class BottlesParser(BaseExternalParser):
    """Parser for programs configured in Bottles."""

    def platform_name(self) -> str:
        return "Bottles"

    def is_available(self) -> bool:
        """Check if PyYAML is installed and any Bottles data directory exists."""
        if not _HAS_YAML:
            return False
        return any(p.is_dir() for p in self._get_base_paths())

    def get_config_paths(self) -> list[Path]:
        return self._get_base_paths()

    def read_games(self) -> list[ExternalGame]:
        """Scan External_Programs and library.yml across all bottles."""
        if not _HAS_YAML:
            return []
        games: list[ExternalGame] = []
        seen_names: set[str] = set()

        for base in self._get_base_paths():
            is_flatpak = base == _FLATPAK_BASE
            bottles_dir = base / "bottles"
            if not bottles_dir.is_dir():
                continue

            for bottle_dir in bottles_dir.iterdir():
                if not bottle_dir.is_dir():
                    continue
                yml_path = bottle_dir / "bottle.yml"
                if not yml_path.exists():
                    continue

                self._parse_bottle(yml_path, is_flatpak, games, seen_names)

            # Also check library.yml
            library_path = base / "library.yml"
            if library_path.exists():
                self._parse_library(library_path, is_flatpak, games, seen_names)

        logger.info("Found %d programs in Bottles", len(games))
        return games

    def _parse_bottle(
        self,
        yml_path: Path,
        is_flatpak: bool,
        games: list[ExternalGame],
        seen_names: set[str],
    ) -> None:
        """Parse a single bottle.yml for External_Programs."""
        try:
            data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            logger.warning("Failed to read %s: %s", yml_path, e)
            return

        if not isinstance(data, dict):
            return

        bottle_name = data.get("Name", yml_path.parent.name)
        external_programs = data.get("External_Programs", {})
        if not isinstance(external_programs, dict):
            return

        for _uuid, prog in external_programs.items():
            if not isinstance(prog, dict):
                continue
            name = prog.get("name", "")
            if not name or name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

            launch_cmd = self._build_launch_command(bottle_name, name, is_flatpak)

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=prog.get("id", ""),
                    name=name,
                    executable=prog.get("executable"),
                    launch_command=launch_cmd,
                    platform_metadata=(("bottle", bottle_name),),
                )
            )

    def _parse_library(
        self,
        library_path: Path,
        is_flatpak: bool,
        games: list[ExternalGame],
        seen_names: set[str],
    ) -> None:
        """Parse library.yml for curated game entries."""
        try:
            data = yaml.safe_load(library_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            logger.warning("Failed to read %s: %s", library_path, e)
            return

        if not isinstance(data, dict):
            return

        for _uuid, entry in data.items():
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", "")
            if not name or name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

            bottle_name = entry.get("bottle", {}).get("name", "")
            launch_cmd = self._build_launch_command(bottle_name, name, is_flatpak) if bottle_name else ""

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=str(_uuid),
                    name=name,
                    launch_command=launch_cmd,
                    platform_metadata=(("bottle", bottle_name),) if bottle_name else (),
                )
            )

    @staticmethod
    def _build_launch_command(bottle_name: str, program_name: str, is_flatpak: bool) -> str:
        if is_flatpak:
            return f"flatpak run com.usebottles.bottles --run " f'--bottle="{bottle_name}" --program="{program_name}"'
        return f"bottles:run/{bottle_name}/{program_name}"

    @staticmethod
    def _get_base_paths() -> list[Path]:
        return [_get_bottles_base(), _FLATPAK_BASE]
