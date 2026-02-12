# src/core/local_games_loader.py

"""
Scans local Steam library folders to find installed games.

This module reads Steam's appmanifest_*.acf files across all configured library
folders to discover installed games. It does NOT load appinfo.vdf, which is
handled separately by AppInfoManager for better performance.
"""

from __future__ import annotations


import logging
import vdf
from pathlib import Path
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.local_loader")

__all__ = ["LocalGamesLoader"]


class LocalGamesLoader:
    """
    Loads installed games from local Steam files without requiring API access.

    This class scans Steam library folders for appmanifest files and parses
    them to extract information about installed games.
    """

    def __init__(self, steam_path: Path):
        """
        Initializes the LocalGamesLoader.

        Args:
            steam_path (Path): Path to the Steam installation directory.
        """
        self.steam_path = steam_path
        self.steamapps_path = steam_path / "steamapps"
        # appinfo.vdf is now ONLY loaded via AppInfoManager
        self.appinfo_vdf_path = steam_path / "appcache" / "appinfo.vdf"

    def get_all_games(self) -> list[dict]:
        """
        Loads all installed games from manifest files across all libraries.

        This method scans all configured Steam library folders and parses
        appmanifest_*.acf files to build a list of installed games.

        Note:
            appinfo.vdf is NO LONGER loaded here. AppInfoManager handles this
            on-demand for better performance.

        Returns:
            list[Dict]: A list of dictionaries, each containing 'appid', 'name',
                       and 'installdir' for an installed game.
        """
        all_games = {}

        # 1. Installed Games (from Library Folders)
        installed = self.get_installed_games()
        for game in installed:
            all_games[str(game["appid"])] = game

        logger.info(t("logs.local_loader.loaded_total", count=len(all_games)))
        return list(all_games.values())

    def get_installed_games(self) -> list[dict]:
        """
        Reads all installed games from appmanifest_*.acf files across all libraries.

        This method discovers all Steam library folders and scans each one for
        appmanifest files, parsing them to extract game information.

        Returns:
            list[Dict]: A list of dictionaries containing game data (appid, name, installdir).
        """
        all_installed = []

        # Get Libraries (Linux Native Paths)
        library_folders = self.get_library_folders()

        logger.info(t("logs.local_loader.scanning_libraries", count=len(library_folders)))

        for lib_path in library_folders:
            # Manifests are typically in steamapps
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
        """
        Finds all Steam library folders based on libraryfolders.vdf.

        This method reads the libraryfolders.vdf file to discover all configured
        Steam library locations. It reads Linux paths (e.g., /mnt/...) directly.

        Returns:
            list[Path]: A list of Path objects representing all Steam library folders.
        """
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
        """
        Parses a single appmanifest_*.acf file.

        Args:
            manifest_path (Path): Path to the appmanifest file.

        Returns:
            dict | None: A dictionary containing 'appid', 'name', and 'installdir',
                           or None if parsing failed.
        """
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
        """
        Extracts playtime data from localconfig.vdf.

        This method reads the localconfig.vdf file and extracts the playtime
        (in minutes) for each game. Steam stores playtime in seconds, so the
        value is converted to minutes.

        Args:
            localconfig_path (Path): Path to the localconfig.vdf file.

        Returns:
            dict[str, int]: A dictionary mapping app_id (as string) to playtime in minutes.
        """
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
                    # Steam stores playtime in seconds, converting to minutes.
                    playtimes[app_id] = int(app_data["playtime"]) // 60

        except (OSError, ValueError, KeyError, SyntaxError, AttributeError):
            pass  # Fail silently on parsing errors

        return playtimes
