#
# steam_library_manager/core/local_games_loader.py
# Scan Steam library folders for installed games via appmanifest files
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations


import logging
import vdf
from pathlib import Path
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.local_loader")

__all__ = ["LocalGamesLoader"]


class LocalGamesLoader:
    """Discovers installed games by scanning appmanifest_*.acf files."""

    def __init__(self, steam_path: Path):
        self.steam_path = steam_path
        self.steamapps_path = steam_path / "steamapps"
        self.appinfo_vdf_path = steam_path / "appcache" / "appinfo.vdf"

    def get_all_games(self) -> list[dict]:
        """All installed games from manifest files across all libraries."""
        all_games = {}

        installed = self.get_installed_games()
        for game in installed:
            all_games[str(game["appid"])] = game

        logger.info(t("logs.local_loader.loaded_total", count=len(all_games)))
        return list(all_games.values())

    def get_installed_games(self) -> list[dict]:
        """Parse appmanifest_*.acf files across all library folders."""
        all_installed = []

        library_folders = self.get_library_folders()

        logger.info(t("logs.local_loader.scanning_libraries", count=len(library_folders)))

        for lib_path in library_folders:
            search_dirs = [lib_path / "steamapps", lib_path]

            manifests_found_in_lib = 0

            for folder in search_dirs:
                if not folder.exists():
                    continue

                manifest_files = list(folder.glob("appmanifest_*.acf"))
                if not manifest_files:
                    continue

                manifests_found_in_lib += len(manifest_files)

                for manifest in manifest_files:
                    try:
                        game_data = self._parse_manifest(manifest)
                        if game_data:
                            all_installed.append(game_data)
                    except (OSError, ValueError):
                        pass

            if manifests_found_in_lib > 0:
                logger.info(t("logs.local_loader.found_manifests_in_path", path=lib_path, count=manifests_found_in_lib))

        return all_installed

    def get_library_folders(self) -> list[Path]:
        """All Steam library paths from libraryfolders.vdf."""
        folders = [self.steam_path]

        possible_vdfs = [self.steamapps_path / "libraryfolders.vdf", self.steam_path / "config" / "libraryfolders.vdf"]

        libraryfolders_vdf = None
        for p in possible_vdfs:
            if p.exists():
                libraryfolders_vdf = p
                break

        if not libraryfolders_vdf:
            logger.info(t("logs.local_loader.no_library_file"))
            return folders

        try:
            with open(libraryfolders_vdf, "r", encoding="utf-8") as f:
                data = vdf.load(f)

            library_data = data.get("libraryfolders", data)

            for key, value in library_data.items():
                if isinstance(value, dict):
                    path_str = value.get("path")
                    if not path_str:
                        continue

                    path_obj = Path(path_str)

                    if path_obj.exists():
                        if path_obj not in folders:
                            folders.append(path_obj)
                    else:
                        logger.info(t("logs.local_loader.path_not_exists", path=path_str))

        except (OSError, ValueError, KeyError, SyntaxError) as e:
            logger.error(t("logs.local_loader.library_error", error=e))

        return list(set(folders))

    @staticmethod
    def _parse_manifest(manifest_path: Path) -> dict | None:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = vdf.load(f)
                app_state = data.get("AppState", {})
                if not app_state:
                    return None
                return {
                    "appid": int(app_state.get("appid", 0)),
                    "name": app_state.get("name", "Unknown"),
                    "installdir": app_state.get("installdir", ""),
                }
        except (OSError, ValueError, KeyError, SyntaxError):
            return None

    @staticmethod
    def get_playtime_from_localconfig(localconfig_path: Path) -> dict[str, int]:
        """Extract per-app playtime (minutes) from localconfig.vdf."""
        playtimes = {}
        if not localconfig_path.exists():
            return playtimes

        try:
            with open(localconfig_path, "r", encoding="utf-8") as f:
                data = vdf.load(f)

            apps = (
                data.get("UserLocalConfigStore", {})
                .get("Software", {})
                .get("Valve", {})
                .get("Steam", {})
                .get("Apps", {})
            )

            for app_id, app_data in apps.items():
                if "playtime" in app_data:
                    playtimes[app_id] = int(app_data["playtime"]) // 60

        except (OSError, ValueError, KeyError, SyntaxError, AttributeError):
            pass  # Fail silently on parsing errors

        return playtimes
