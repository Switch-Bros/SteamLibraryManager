# src/core/localconfig_helper.py

"""
LocalConfig Helper - Minimal VDF parser for Steam's localconfig.vdf

Only handles:
- Hidden status (games hidden from library)
- Expanded/Collapsed state (category UI state in Steam client)

Collections/Categories are managed by cloud_storage_parser!
"""
from __future__ import annotations


import logging
import vdf
from pathlib import Path
from typing import List, Dict

from src.utils.i18n import t



logger = logging.getLogger("steamlibmgr.localconfig")

class LocalConfigHelper:
    """Minimal helper for localconfig.vdf operations."""

    def __init__(self, config_path: str):
        """Initialize the helper.

        Args:
            config_path: Path to localconfig.vdf file
        """
        self.config_path = Path(config_path)
        self.data: Dict = {}
        self.apps: Dict = {}
        self.modified = False

    def load(self) -> bool:
        """Load localconfig.vdf file.

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = vdf.load(f)

            # Navigate to Apps section
            steam_section = (self.data.get('UserLocalConfigStore', {})
                             .get('Software', {})
                             .get('Valve', {})
                             .get('Steam', {}))

            self.apps = steam_section.get('Apps', {})
            return True

        except FileNotFoundError:
            logger.error(t('logs.localconfig.not_found', path=self.config_path))
            return False
        except Exception as e:
            logger.error(t('logs.localconfig.load_error', error=e))
            return False

    def save(self) -> bool:
        """Save localconfig.vdf file.

        Returns:
            True if successful, False otherwise
        """
        if not self.modified:
            return True

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                vdf.dump(self.data, f, pretty=True)
            self.modified = False
            return True

        except OSError as e:
            logger.error(t('logs.localconfig.save_error', error=e))
            return False

    # ===== HIDDEN STATUS =====

    def get_hidden_apps(self) -> List[str]:
        """Get list of hidden app IDs.

        Returns:
            List of app IDs that are hidden
        """
        hidden = []
        for app_id, app_data in self.apps.items():
            if app_data.get('hidden', '0') == '1':
                hidden.append(app_id)
        return hidden

    def set_app_hidden(self, app_id: str, hidden: bool):
        """Set hidden status for an app.

        Args:
            app_id: Steam app ID
            hidden: True to hide, False to show
        """
        app_id = str(app_id)

        if app_id not in self.apps:
            self.apps[app_id] = {}

        self.apps[app_id]['hidden'] = '1' if hidden else '0'
        self.modified = True

    # ===== EXPANDED/COLLAPSED STATE =====

    def get_expanded_state(self, category_id: str) -> bool:
        """Get expanded state for a category.

        Args:
            category_id: Category/collection ID

        Returns:
            True if expanded, False if collapsed
        """
        if category_id not in self.apps:
            return True  # Default: expanded

        cloud_state = self.apps[category_id].get('CloudLocalAppState', {})
        expanded = cloud_state.get('Expanded', '1')
        return expanded == '1'

    def set_expanded_state(self, category_id: str, expanded: bool):
        """Set expanded state for a category.

        Args:
            category_id: Category/collection ID
            expanded: True to expand, False to collapse
        """
        if category_id not in self.apps:
            self.apps[category_id] = {}

        if 'CloudLocalAppState' not in self.apps[category_id]:
            self.apps[category_id]['CloudLocalAppState'] = {}

        self.apps[category_id]['CloudLocalAppState']['Expanded'] = '1' if expanded else '0'
        self.modified = True

    def get_all_expanded_states(self) -> Dict[str, bool]:
        """Get expanded states for all categories.

        Returns:
            Dictionary mapping category IDs to expanded state (True/False)
        """
        states = {}
        for app_id, app_data in self.apps.items():
            cloud_state = app_data.get('CloudLocalAppState', {})
            if 'Expanded' in cloud_state:
                expanded = cloud_state.get('Expanded', '1')
                states[app_id] = (expanded == '1')
        return states

    # ===== CLEANUP =====

    def remove_app(self, app_id: str) -> bool:
        """Remove app entry from localconfig (cleanup ghost entries).

        Args:
            app_id: Steam app ID to remove

        Returns:
            True if app was removed, False if not found
        """
        app_id = str(app_id)

        if app_id in self.apps:
            del self.apps[app_id]
            self.modified = True
            return True

        return False