"""
Local Games Loader - Multi-Library Support + appinfo.vdf names
Speichern als: src/core/local_games_loader.py
"""

import vdf
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from src.utils.i18n import t


class LocalGamesLoader:
    """Lädt Spiele aus lokalen Steam-Dateien ohne API"""

    def __init__(self, steam_path: Path):
        self.steam_path = steam_path
        self.steamapps_path = steam_path / 'steamapps'
        self.appinfo_vdf_path = steam_path / 'appcache' / 'appinfo.vdf'

    def get_all_games(self) -> List[Dict]:
        """
        Lädt ALLE Spiele (installiert + nicht-installiert)
        """
        all_games = {}

        # 1. Installierte Spiele (haben die besten Daten)
        installed = self.get_installed_games()
        for game in installed:
            all_games[str(game['appid'])] = game

        # 2. Spiele aus appinfo.vdf (alle bekannten Spiele)
        appinfo_games = self.get_games_from_appinfo()
        for app_id, name in appinfo_games.items():
            if app_id not in all_games:
                all_games[app_id] = {
                    'appid': int(app_id),
                    'name': name,
                    'installdir': '',
                    'LastUpdated': 0,
                    'SizeOnDisk': 0,
                }

        print(t('logs.local_loader.loaded_total', count=len(all_games)))
        return list(all_games.values())

    def get_installed_games(self) -> List[Dict]:
        """
        Liest alle installierten Spiele aus appmanifest_*.acf Dateien
        Multi-Library Support!
        """
        all_installed = []
        library_folders = self.get_library_folders()

        print(t('logs.local_loader.scanning_libraries', count=len(library_folders)))

        for lib_path in library_folders:
            steamapps = lib_path / 'steamapps'
            if not steamapps.exists():
                continue

            manifest_files = list(steamapps.glob('appmanifest_*.acf'))
            print(t('logs.local_loader.found_manifests', path=lib_path.name, count=len(manifest_files)))

            for manifest in manifest_files:
                try:
                    game_data = self._parse_manifest(manifest)
                    if game_data:
                        all_installed.append(game_data)
                except Exception as e:
                    print(t('logs.local_loader.parse_error', file=manifest.name, error=e))

        print(t('logs.local_loader.loaded_installed', count=len(all_installed)))
        return all_installed

    def get_games_from_appinfo(self) -> Dict[str, str]:
        """
        Lädt Spiel-Namen aus appinfo.vdf
        """
        if not self.appinfo_vdf_path.exists():
            print(t('logs.local_loader.no_appinfo'))
            return {}

        try:
            from src.utils.appinfo_vdf_parser import AppInfoParser

            print(t('logs.local_loader.reading_appinfo'))
            data = AppInfoParser.load(self.appinfo_vdf_path)

            games = {}
            for app_id, app_data in data.items():
                try:
                    # Versuche verschiedene Locations für den Namen
                    name = None

                    # Location 1: common.name (häufigster Fall)
                    if isinstance(app_data, dict):
                        if 'common' in app_data:
                            common = app_data['common']
                            if isinstance(common, dict) and 'name' in common:
                                name = common['name']

                        # Location 2: Direkt 'name' key
                        if not name and 'name' in app_data:
                            name = app_data['name']

                    # Nur hinzufügen wenn Name gefunden
                    if name and isinstance(name, str) and name.strip():
                        games[app_id] = name.strip()

                except Exception as e:
                    # Stilles Überspringen bei einzelnen Fehlern
                    pass

            print(t('logs.local_loader.loaded_from_appinfo', count=len(games)))
            return games

        except Exception as e:
            print(t('logs.local_loader.appinfo_error', error=e))
            import traceback
            traceback.print_exc()  # Zeigt den vollständigen Fehler
            return {}

    def _parse_manifest(self, manifest_path: Path) -> Optional[Dict]:
        """Parse a single appmanifest file"""
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)
                app_state = data.get('AppState', {})

                if not app_state:
                    return None

                app_id = app_state.get('appid')
                name = app_state.get('name', f'App {app_id}')

                return {
                    'appid': int(app_id),
                    'name': name,
                    'installdir': app_state.get('installdir', ''),
                    'LastUpdated': int(app_state.get('LastUpdated', 0)),
                    'SizeOnDisk': int(app_state.get('SizeOnDisk', 0)),
                    'BytesToDownload': int(app_state.get('BytesToDownload', 0)),
                    'BytesDownloaded': int(app_state.get('BytesDownloaded', 0)),
                }
        except Exception as e:
            return None

    def get_library_folders(self) -> List[Path]:
        """
        Findet alle Steam Library Ordner (Multi-Drive Setup)
        """
        folders = [self.steam_path]
        libraryfolders_vdf = self.steamapps_path / 'libraryfolders.vdf'

        if not libraryfolders_vdf.exists():
            print(t('logs.local_loader.no_library_file'))
            return folders

        try:
            with open(libraryfolders_vdf, 'r', encoding='utf-8') as f:
                data = vdf.load(f)
                library_data = data.get('libraryfolders', {})

                for key, value in library_data.items():
                    if key.isdigit() and isinstance(value, dict):
                        path = value.get('path')
                        if path:
                            lib_path = Path(path)
                            if lib_path.exists():
                                folders.append(lib_path)
                                print(t('logs.local_loader.found_library', path=path))
        except Exception as e:
            print(t('logs.local_loader.library_error', error=e))

        return folders

    def get_playtime_from_localconfig(self, localconfig_path: Path) -> Dict[str, int]:
        """
        Extrahiert Playtime aus localconfig.vdf
        Returns: {app_id: playtime_minutes}
        """
        playtimes = {}

        if not localconfig_path.exists():
            return playtimes

        try:
            with open(localconfig_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)

            apps = data.get('UserLocalConfigStore', {}).get('Software', {}).get('Valve', {}).get('Steam', {}).get(
                'Apps', {})

            for app_id, app_data in apps.items():
                if 'playtime' in app_data:
                    # Playtime ist in Sekunden gespeichert
                    playtime_seconds = int(app_data['playtime'])
                    playtime_minutes = playtime_seconds // 60
                    playtimes[app_id] = playtime_minutes

            print(t('logs.local_loader.loaded_playtime', count=len(playtimes)))

        except Exception as e:
            print(t('logs.local_loader.playtime_error', error=e))

        return playtimes