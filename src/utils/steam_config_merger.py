# src/utils/steam_config_merger.py

"""
Steam configuration merger for transferring categories between platforms.

This utility transfers game categories (tags) between Windows (sharedconfig.vdf)
and Linux (localconfig.vdf) with support for multiple merge strategies, automatic
backups, and dry-run mode for testing.
"""
import logging
import shutil
from pathlib import Path
from typing import Tuple, Optional, List, Callable
from enum import Enum

from src.core.localconfig_parser import LocalConfigParser
from src.utils.i18n import t


class MergeStrategy(Enum):
    """
    Strategy for handling tag conflicts during merge operations.

    Attributes:
        OVERWRITE: Source replaces target (default).
        MERGE: Combine unique tags from both source and target.
        SKIP_EXISTING: Only add tags to apps that have no existing tags.
    """
    OVERWRITE = "overwrite"
    MERGE = "merge"
    SKIP_EXISTING = "skip_existing"


class SteamConfigMerger:
    """
    Merges Steam configuration files between different platforms.

    This class provides functionality to transfer game categories (tags) from
    one Steam configuration file to another, with support for different merge
    strategies, automatic backups, and progress tracking.
    """

    def __init__(self):
        """Initializes the SteamConfigMerger."""
        self.logger = logging.getLogger("SteamConfigMerger")

    @staticmethod
    def _find_apps_section(data: dict) -> Optional[dict]:
        """
        Dynamically finds the 'apps' section in a VDF dictionary.

        This method handles both UserLocalConfigStore (localconfig.vdf) and
        UserRoamingConfigStore (sharedconfig.vdf) formats. It returns a reference
        to the dictionary, allowing direct modification.

        Args:
            data (dict): The parsed VDF data.

        Returns:
            Optional[dict]: A reference to the 'apps' dictionary, or None if not found.
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

    @staticmethod
    def _create_backup(target_path: Path) -> Optional[Path]:
        """
        Creates a backup of the target file before modification.

        This method first attempts to use the BackupManager from core. If that fails,
        it creates a simple backup with a .backup extension.

        Args:
            target_path (Path): Path to the file to back up.

        Returns:
            Optional[Path]: Path to the backup file, or None if backup failed.
        """
        try:
            # Import backup manager from core
            from src.core.backup_manager import BackupManager

            # Create backup directory if needed
            backup_dir = target_path.parent.parent.parent / 'data' / 'backups'
            backup_manager = BackupManager(backup_dir)

            # Create backup
            backup_path = backup_manager.create_backup(target_path)
            return backup_path
        except (ImportError, OSError, IOError):
            # If BackupManager fails, create simple backup
            try:
                backup_path = target_path.with_suffix(target_path.suffix + '.backup')
                shutil.copy2(target_path, backup_path)
                return backup_path
            except (OSError, IOError) as fallback_error:
                print(t('logs.backup.backup_failed', error=str(fallback_error)))
                return None

    def merge_tags(
            self,
            source_path: Path,
            target_path: Path,
            strategy: MergeStrategy = MergeStrategy.OVERWRITE,
            create_backup: bool = True,
            dry_run: bool = False,
            progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[bool, str, List[str]]:
        """
        Transfers categories from source_path to target_path.

        This method reads game categories from the source file and merges them into
        the target file according to the specified strategy. It supports automatic
        backups, dry-run mode for testing, and progress callbacks for UI integration.

        Args:
            source_path (Path): Path to source VDF file (e.g., sharedconfig.vdf from Windows).
            target_path (Path): Path to target VDF file (e.g., localconfig.vdf on Linux).
            strategy (MergeStrategy): Merge strategy to use. Defaults to OVERWRITE.
            create_backup (bool): Whether to create a backup before modifying target. Defaults to True.
            dry_run (bool): If True, simulate changes without saving. Defaults to False.
            progress_callback (Optional[Callable[[int, int, str], None]]): Optional callback
                function(current, total, app_id) for progress updates.

        Returns:
            Tuple[bool, str, List[str]]: A tuple containing:
                - Success (bool): Whether the operation succeeded.
                - Message (str): A human-readable status message.
                - Changes (List[str]): Descriptions of all modifications made.
        """
        changes = []

        # 1. Validate paths
        if not source_path.exists():
            return False, t('logs.merger.source_missing', path=source_path), []

        if not target_path.exists():
            return False, t('logs.merger.target_missing', path=target_path), []

        # 2. Load Source
        parser_source = LocalConfigParser(source_path)
        if not parser_source.load():
            return False, t('logs.merger.load_error_source'), []

        # 3. Load Target
        parser_target = LocalConfigParser(target_path)
        if not parser_target.load():
            return False, t('logs.merger.load_error_target'), []

        # 4. Find Apps Sections
        source_apps = self._find_apps_section(parser_source.data)
        if source_apps is None:
            return False, t('logs.merger.no_apps_section', file=source_path.name), []

        target_apps = self._find_apps_section(parser_target.data)
        if target_apps is None:
            return False, t('logs.merger.no_apps_section', file=target_path.name), []

        # 5. Merge Logic
        count_merged = 0
        total_apps = len(source_apps)

        for i, (app_id, app_data) in enumerate(source_apps.items()):
            # Progress callback
            if progress_callback:
                progress_callback(i, total_apps, app_id)

            # Steam uses 'tags' or 'Tags' keys
            tags = app_data.get('tags') or app_data.get('Tags')

            if not tags:
                continue

            # Normalize source tags to list
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

            # Apply merge strategy
            final_tags = None

            if strategy == MergeStrategy.OVERWRITE:
                # Source replaces target
                if sorted(source_tag_list) != sorted(target_tag_list):
                    final_tags = source_tag_list
                    changes.append(f"App {app_id}: Overwrite {len(target_tag_list)} → {len(source_tag_list)} tags")

            elif strategy == MergeStrategy.MERGE:
                # Combine unique tags from both
                merged_tags = list(set(source_tag_list + target_tag_list))
                if sorted(merged_tags) != sorted(target_tag_list):
                    final_tags = merged_tags
                    changes.append(
                        f"App {app_id}: Merged {len(target_tag_list)} + {len(source_tag_list)} → {len(merged_tags)} tags")

            elif strategy == MergeStrategy.SKIP_EXISTING:
                # Only update if target has no tags
                if not target_tag_list and source_tag_list:
                    final_tags = source_tag_list
                    changes.append(f"App {app_id}: Added {len(source_tag_list)} tags (was empty)")

            # Apply changes (if not dry-run)
            if final_tags is not None:
                if not dry_run:
                    # Ensure app_id exists in target
                    if app_id not in target_apps:
                        target_apps[app_id] = {}

                    # Write tags in correct format (Dict "0": "Tag", "1": "Tag")
                    new_tags_dict = {str(idx): tag for idx, tag in enumerate(final_tags)}
                    target_apps[app_id]['tags'] = new_tags_dict

                count_merged += 1

        # 6. Final callback
        if progress_callback:
            progress_callback(total_apps, total_apps, "complete")

        # 7. Handle Results
        if count_merged == 0:
            return True, t('logs.merger.no_changes'), []

        if dry_run:
            return True, t('logs.merger.dry_run_complete', count=count_merged, changes=len(changes)), changes

        # 8. Create Backup (if requested)
        if create_backup:
            backup_path = self._create_backup(target_path)
            if backup_path:
                changes.append(f"{t('emoji.success')} {t('logs.backup.created', name=backup_path.name)}")
            else:
                return False, t('logs.merger.backup_failed'), changes

        # 9. Save Target
        if parser_target.save():
            return True, t('logs.merger.success',
                           count=count_merged,
                           path=target_path.name,
                           strategy=strategy.value), changes
        else:
            return False, t('logs.merger.save_error'), changes
