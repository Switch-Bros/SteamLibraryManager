#
# steam_library_manager/integrations/external_games/bottles_parser.py
# Parser for Bottles (Wine/Proton manager) installed games
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

_FLATPAK_BASE = Path.home() / ".var" / "app" / "com.usebottles.bottles" / "data" / "bottles"


def _get_base():
    # XDG-based Bottles data directory
    xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg) / "bottles"


def _load_yaml(path):
    # load YAML, return None on error
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        logger.warning("Failed to read %s: %s" % (path, e))
        return None
    return data if isinstance(data, dict) else None


class BottlesParser(BaseExternalParser):
    # parser for Bottles programs

    def platform_name(self):
        return "Bottles"

    def is_available(self):
        # need PyYAML and at least one data dir
        if not _HAS_YAML:
            return False
        return any(p.is_dir() for p in self._get_base_paths())

    def get_config_paths(self):
        # possible base dirs (not individual bottle.yml files)
        return self._get_base_paths()

    def read_games(self):
        # scan all bottles for External_Programs + library.yml
        if not _HAS_YAML:
            return []

        games = []
        seen = set()

        for base in self._get_base_paths():
            bottles = base / "bottles"
            is_fp = base == _FLATPAK_BASE

            if bottles.is_dir():
                for d in bottles.iterdir():
                    yml = d / "bottle.yml"
                    if d.is_dir() and yml.exists():
                        self._parse_bottle(yml, is_fp, games, seen)

            # global library with curated entries
            lib = base / "library.yml"
            if lib.exists():
                self._parse_lib(lib, is_fp, games, seen)

        logger.info("Found %d programs in Bottles" % len(games))
        return games

    def _parse_bottle(self, yml, is_fp, games, seen):
        # extract External_Programs from bottle.yml
        data = _load_yaml(yml)
        if data is None:
            return

        bname = data.get("Name", yml.parent.name)
        progs = data.get("External_Programs", {})
        if not isinstance(progs, dict):
            return

        for _uuid, prog in progs.items():
            if not isinstance(prog, dict):
                continue
            name = prog.get("name", "")
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=prog.get("id", ""),
                    name=name,
                    executable=prog.get("executable"),
                    launch_command=self._cmd(bname, name, is_fp),
                    platform_metadata=(("bottle", bname),),
                )
            )

    def _parse_lib(self, lib, is_fp, games, seen):
        data = _load_yaml(lib)
        if data is None:
            return

        for _uuid, entry in data.items():
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", "")
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)

            bname = entry.get("bottle", {}).get("name", "")
            # only build command when we know which bottle
            cmd = self._cmd(bname, name, is_fp) if bname else ""

            games.append(
                ExternalGame(
                    platform=self.platform_name(),
                    platform_app_id=str(_uuid),
                    name=name,
                    launch_command=cmd,
                    platform_metadata=(("bottle", bname),) if bname else (),
                )
            )

    @staticmethod
    def _cmd(bname, pname, is_fp):
        if is_fp:
            return "flatpak run com.usebottles.bottles --run " '--bottle="%s" --program="%s"' % (bname, pname)
        return "bottles:run/%s/%s" % (bname, pname)

    @staticmethod
    def _get_base_paths():
        return [_get_base(), _FLATPAK_BASE]
