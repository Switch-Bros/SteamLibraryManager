"""
localconfig.vdf Parser und Writer
Liest und schreibt Steam's localconfig.vdf Datei
Speichern als: src/core/localconfig_parser.py
"""

import vdf
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from src.utils.i18n import t


class LocalConfigParser:
    """Parser für Steam's localconfig.vdf"""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.data: Dict = {}
        self.apps: Dict = {}
        self.modified = False

    def load(self) -> bool:
        """Lade localconfig.vdf"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = vdf.load(f)

            # Navigiere zur Apps-Sektion
            try:
                self.apps = self.data['UserLocalConfigStore']['Software']['Valve']['Steam']['Apps']
            except KeyError:
                print(t('logs.parser.apps_not_found'))
                self.apps = {}

            return True

        except FileNotFoundError:
            print(t('logs.parser.file_not_found', path=self.config_path))
            return False
        except Exception as e:
            print(t('logs.parser.load_error', error=e))
            return False

    def save(self, create_backup: bool = True) -> bool:
        """Speichere localconfig.vdf"""
        if not self.modified:
            return True

        if create_backup:
            # Backup erstellen
            backup_path = self.config_path.with_suffix('.vdf.bak')
            try:
                shutil.copy2(self.config_path, backup_path)
            except OSError:
                pass  # Backup fehlgeschlagen, nicht kritisch

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                vdf.dump(self.data, f, pretty=True)
            self.modified = False
            return True
        except OSError as e:
            print(t('logs.parser.save_error', error=e))
            return False

    def get_all_app_ids(self) -> List[str]:
        return list(self.apps.keys())

    def get_app_categories(self, app_id: str) -> List[str]:
        app_data = self.apps.get(str(app_id), {})
        tags = app_data.get('tags', {})
        if isinstance(tags, dict):
            return list(tags.values())
        return []

    def set_app_categories(self, app_id: str, categories: List[str]):
        if str(app_id) not in self.apps:
            self.apps[str(app_id)] = {}

        # Steam speichert Tags als Dict {"0": "Tag1", "1": "Tag2"}
        tags_dict = {str(i): cat for i, cat in enumerate(categories)}
        self.apps[str(app_id)]['tags'] = tags_dict
        self.modified = True

    def add_app_category(self, app_id: str, category: str):
        categories = self.get_app_categories(app_id)
        if category not in categories:
            categories.append(category)
            self.set_app_categories(app_id, categories)

    def remove_app_category(self, app_id: str, category: str):
        categories = self.get_app_categories(app_id)
        if category in categories:
            categories.remove(category)
            self.set_app_categories(app_id, categories)

    def get_apps_in_category(self, category: str) -> List[str]:
        apps = []
        for app_id in self.apps:
            if category in self.get_app_categories(app_id):
                apps.append(app_id)
        return apps

    def rename_category(self, old_name: str, new_name: str):
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if old_name in categories:
                categories = [new_name if c == old_name else c for c in categories]
                self.set_app_categories(app_id, categories)

    def delete_category(self, category: str):
        for app_id in self.apps:
            self.remove_app_category(app_id, category)

    def get_app_data(self, app_id: str) -> Optional[Dict]:
        return self.apps.get(app_id)

    def set_app_data(self, app_id: str, data: Dict):
        self.apps[app_id] = data
        self.modified = True

    def get_uncategorized_apps(self) -> List[str]:
        uncategorized = []
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if not categories or categories == ['favorite']:
                uncategorized.append(app_id)
        return uncategorized


if __name__ == "__main__":
    from src.utils.i18n import init_i18n

    init_i18n('en')

    # Test
    test_config_path = Path("test_localconfig.vdf")
    parser = LocalConfigParser(test_config_path)
    if parser.load():
        print(f"Loaded {len(parser.get_all_app_ids())} apps")