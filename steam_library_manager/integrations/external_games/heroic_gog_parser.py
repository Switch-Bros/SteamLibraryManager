#
# steam_library_manager/integrations/external_games/heroic_gog_parser.py
# Heroic Launcher parser for GOG Galaxy library
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from steam_library_manager.integrations.external_games.base_heroic_parser import BaseHeroicParser
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["HeroicGOGParser"]

logger = logging.getLogger("steamlibmgr.external_games.heroic_gog")

# config file locations
_NATIVE = Path.home() / ".config" / "heroic" / "gog_store" / "installed.json"
_FLATPAK = (
    Path.home() / ".var" / "app" / "com.heroicgameslauncher.hgl" / "config" / "heroic" / "gog_store" / "installed.json"
)

# size pattern: "27.8 MiB", "1.2 GiB"
_SIZE_PATTERN = re.compile(r"([\d.]+)\s*(B|KiB|MiB|GiB|TiB|KB|MB|GB|TB)", re.IGNORECASE)
_SIZE_MULTIPLIERS = {
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


def _parse_size_string(size_str):
    # parse "27.8 MiB" to bytes, returns 0 on garbage
    m = _SIZE_PATTERN.match(size_str.strip())
    if not m:
        return 0
    val = float(m.group(1))
    unit = m.group(2).lower()
    return int(val * _SIZE_MULTIPLIERS.get(unit, 1))


class HeroicGOGParser(BaseHeroicParser):
    """Parser for Heroic GOG games."""

    _RUNNER = "gog"

    def platform_name(self):
        # return platform identifier
        return "Heroic (GOG)"

    def is_available(self):
        # check if config exists
        return self._find_config_file() is not None

    def get_config_paths(self):
        # return possible config locations
        return [_NATIVE, _FLATPAK]

    def read_games(self):
        # read installed games from heroic config
        data, cfg_path = self._load_heroic_config_with_path()

        installed = data.get("installed", []) if isinstance(data, dict) else []
        if not isinstance(installed, list):
            return []

        is_flatpak = self._is_flatpak(cfg_path) if cfg_path else False
        heroic_cfg = cfg_path.parent.parent if cfg_path else None
        games = []

        for entry in installed:
            if not isinstance(entry, dict):
                continue
            if entry.get("is_dlc", False):
                continue  # skip DLC entries

            app_name = entry.get("appName", "")
            install_path = entry.get("install_path", "")
            name = self._resolve_name(app_name, install_path, heroic_cfg)

            raw_size = entry.get("install_size", 0)
            if isinstance(raw_size, str):
                install_size = _parse_size_string(raw_size)
            else:
                install_size = int(raw_size or 0)

            launch_cmd = self._build_heroic_launch_command(app_name, is_flatpak)
            meta = []  # metadata tuples
            if entry.get("version"):
                meta.append(("version", str(entry["version"])))
            if entry.get("language"):
                meta.append(("language", str(entry["language"])))

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=app_name,
                    name=name,
                    install_path=Path(install_path) if install_path else None,
                    launch_command=launch_cmd,
                    install_size=install_size,
                    platform_metadata=tuple(meta),
                )
            )

        logger.info("Found %d GOG games via Heroic", len(games))
        return games

    @staticmethod
    def _resolve_name(app_name, install_path, heroic_cfg):
        # resolve game name from cache or path
        # try cache first, then fall back to directory name
        if heroic_cfg:
            cache_file = heroic_cfg / "store_cache" / ("%s.json" % app_name)
            if cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and data.get("title"):
                        return str(data["title"])
                except (OSError, json.JSONDecodeError):
                    pass  # cache corrupted, ignore

        if install_path:
            return Path(install_path).name

        return app_name
