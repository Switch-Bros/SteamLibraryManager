"""
Steam Configuration Merger
Utility to transfer categories (tags) between Windows (sharedconfig.vdf) and Linux (localconfig.vdf).
"""
import logging
from pathlib import Path
from typing import Tuple, Optional

from src.core.localconfig_parser import LocalConfigParser
from src.utils.i18n import t


class SteamConfigMerger:
    def __init__(self):
        self.logger = logging.getLogger("SteamConfigMerger")

    @staticmethod
    def _find_apps_section(data: dict) -> Optional[dict]:
        """
        Dynamically finds the 'apps' section in a VDF dictionary.
        Handles both UserLocalConfigStore (localconfig) and UserRoamingConfigStore (sharedconfig).
        Returns a reference to the dictionary, allowing direct modification.
        """
        # Possible root keys for different config files
        roots = ['UserLocalConfigStore', 'UserRoamingConfigStore']

        for root in roots:
            if root in data:
                try:
                    # Navigate safe to apps: Root -> Software -> Valve -> Steam -> apps
                    return data[root]['Software']['Valve']['Steam']['apps']
                except KeyError:
                    continue
        return None

    def merge_tags(self, source_path: Path, target_path: Path) -> Tuple[bool, str]:
        """
        Transfers categories from source_path to target_path.
        Returns: (Success: bool, Message: str)
        """
        if not source_path.exists():
            return False, t('tools.merger.source_missing', path=source_path)

        if not target_path.exists():
            return False, t('tools.merger.target_missing', path=target_path)

        # 1. Load Source
        parser_source = LocalConfigParser(source_path)
        if not parser_source.load():
            return False, t('tools.merger.load_error_source')

        # 2. Load Target
        parser_target = LocalConfigParser(target_path)
        if not parser_target.load():
            return False, t('tools.merger.load_error_target')

        # 3. Find Apps Sections
        # Calling static method via self is valid in Python, or use SteamConfigMerger._find_apps_section
        source_apps = self._find_apps_section(parser_source.data)
        if source_apps is None:
            return False, t('tools.merger.no_apps_section', file=source_path.name)

        target_apps = self._find_apps_section(parser_target.data)
        if target_apps is None:
            # If target has no apps section yet, we might need to create it,
            # but usually a valid steam config has it.
            return False, t('tools.merger.no_apps_section', file=target_path.name)

        # 4. Merge Logic
        count_merged = 0

        for app_id, app_data in source_apps.items():
            # Steam uses 'tags' or 'Tags' keys
            tags = app_data.get('tags') or app_data.get('Tags')

            if tags:
                # Normalize tags to a list of values
                if isinstance(tags, dict):
                    source_tag_list = list(tags.values())
                elif isinstance(tags, list):
                    source_tag_list = tags
                else:
                    continue

                # Get target tags (if any)
                target_app_data = target_apps.get(app_id, {})
                current_tags_raw = target_app_data.get('tags') or target_app_data.get('Tags') or {}

                if isinstance(current_tags_raw, dict):
                    target_tag_list = list(current_tags_raw.values())
                elif isinstance(current_tags_raw, list):
                    target_tag_list = current_tags_raw
                else:
                    target_tag_list = []

                # Compare and update if different
                # We overwrite target with source logic here (Source is Master)
                if sorted(source_tag_list) != sorted(target_tag_list):
                    # Ensure app_id exists in target
                    if app_id not in target_apps:
                        target_apps[app_id] = {}

                    # Write tags in correct format (Dict "0": "Tag", "1": "Tag")
                    # This modifies parser_target.data directly because target_apps is a reference
                    new_tags_dict = {str(i): tag for i, tag in enumerate(source_tag_list)}
                    target_apps[app_id]['tags'] = new_tags_dict

                    count_merged += 1

        # 5. Save Result
        if count_merged > 0:
            if parser_target.save():
                return True, t('tools.merger.success', count=count_merged, path=target_path.name)
            else:
                return False, t('tools.merger.save_error')
        else:
            return True, t('tools.merger.no_changes')