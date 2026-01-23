"""
Local Games Loader - Multi-Library Support (Linux Native)
Speichern als: src/core/local_games_loader.py
"""

import vdf
from pathlib import Path
from typing import List, Dict, Optional
from src.utils.i18n import t


class LocalGamesLoader:
    """Lädt Spiele aus lokalen Steam-Dateien ohne API"""

    def __init__(self, steam_path: Path):
        self.steam_path = steam_path
        self.steamapps_path = steam_path / 'steamapps'
        self.appinfo_vdf_path = steam_path / 'appcache' / 'appinfo.vdf'

    def get_all_games(self) -> List[Dict]:
        """Lädt ALLE Spiele (installiert + nicht-installiert)"""
        all_games = {}

        # 1. Installierte Spiele (aus Library Folders)
        installed = self.get_installed_games()
        for game in installed:
            all_games[str(game['appid'])] = game

        # 2. Spiele aus appinfo.vdf (Metadaten für alle)
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
        """Liest alle installierten Spiele aus appmanifest_*.acf Dateien"""
        all_installed = []

        # Holt Libraries (Linux Native Paths)
        library_folders = self.get_library_folders()

        print(t('logs.local_loader.scanning_libraries', count=len(library_folders)))

        for lib_path in library_folders:
            # Manifests liegen normalerweise in steamapps, manchmal direkt im Library Root
            search_dirs = [lib_path / 'steamapps', lib_path]

            manifests_found_in_lib = 0

            for folder in search_dirs:
                if not folder.exists(): continue

                manifest_files = list(folder.glob('appmanifest_*.acf'))
                if not manifest_files: continue

                manifests_found_in_lib += len(manifest_files)

                for manifest in manifest_files:
                    try:
                        game_data = self._parse_manifest(manifest)
                        if game_data:
                            all_installed.append(game_data)
                    except (OSError, ValueError):
                        pass

            if manifests_found_in_lib > 0:
                print(t('logs.local_loader.found_manifests_in_path', path=lib_path, count=manifests_found_in_lib))

        return all_installed

    def get_library_folders(self) -> List[Path]:
        """
        Findet alle Steam Library Ordner anhand der libraryfolders.vdf.
        Liest direkt die Linux-Pfade (/mnt/...) aus.
        """
        folders = [self.steam_path]

        possible_vdfs = [
            self.steamapps_path / 'libraryfolders.vdf',
            self.steam_path / 'config' / 'libraryfolders.vdf'
        ]

        libraryfolders_vdf = None
        for p in possible_vdfs:
            if p.exists():
                libraryfolders_vdf = p
                break

        if not libraryfolders_vdf:
            print(t('logs.local_loader.no_library_file'))
            return folders

        try:
            with open(libraryfolders_vdf, 'r', encoding='utf-8') as f:
                data = vdf.load(f)

            library_data = data.get('libraryfolders', data)

            for key, value in library_data.items():
                if isinstance(value, dict):
                    path_str = value.get('path')
                    if not path_str: continue

                    path_obj = Path(path_str)

                    if path_obj.exists():
                        if path_obj not in folders:
                            folders.append(path_obj)
                    else:
                        print(t('logs.local_loader.path_not_exists', path=path_str))

        except (OSError, ValueError, KeyError, SyntaxError) as e:
            print(t('logs.local_loader.library_error', error=e))

        return list(set(folders))

    def get_games_from_appinfo(self) -> Dict[str, str]:
        """Lädt Spiel-Namen aus appinfo.vdf"""
        if not self.appinfo_vdf_path.exists():
            return {}

        try:
            # WICHTIG: appinfo.vdf ist eine BINÄRE Datei - muss mit 'rb' geöffnet werden
            from src.utils import appinfo

            with open(self.appinfo_vdf_path, 'rb') as f:
                data = appinfo.load(f)

            games = {}
            for app_id, app_data in data.items():
                name = self._extract_name(app_data)
                if name:
                    games[app_id] = name
            return games
        except (OSError, ValueError, KeyError, AttributeError, ImportError):
            return {}

    def _extract_name(self, app_data) -> Optional[str]:
        """Hilfsfunktion um Namen tief in der Struktur zu finden"""
        if not isinstance(app_data, dict): return None
        # 1. common -> name
        if 'common' in app_data and isinstance(app_data['common'], dict):
            return app_data['common'].get('name')
        # 2. data -> common -> name
        if 'data' in app_data:
            return self._extract_name(app_data['data'])
        # 3. direkt 'name'
        return app_data.get('name')

    @staticmethod
    def _parse_manifest(manifest_path: Path) -> Optional[Dict]:
        """Parse a single appmanifest file"""
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)
                app_state = data.get('AppState', {})
                if not app_state: return None
                return {
                    'appid': int(app_state.get('appid', 0)),
                    'name': app_state.get('name', 'Unknown'),
                    'installdir': app_state.get('installdir', ''),
                }
        except (OSError, ValueError, KeyError, SyntaxError):
            return None

    @staticmethod
    def get_playtime_from_localconfig(localconfig_path: Path) -> Dict[str, int]:
        playtimes = {}
        if not localconfig_path.exists(): return playtimes
        try:
            with open(localconfig_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)
            apps = data.get('UserLocalConfigStore', {}).get('Software', {}).get('Valve', {}).get('Steam', {}).get(
                'Apps', {})
            for app_id, app_data in apps.items():
                if 'playtime' in app_data:
                    playtimes[app_id] = int(app_data['playtime']) // 60
        except (OSError, ValueError, KeyError, SyntaxError, AttributeError):
            pass
        return playtimes