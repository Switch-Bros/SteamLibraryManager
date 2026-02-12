# src/core/backup_manager.py

"""
Manages file backups with automatic rotation.

This module provides functionality to create timestamped backups of configuration
files and automatically rotate (delete) old backups when a maximum limit is reached.
"""
from __future__ import annotations

import logging
import shutil
import glob
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from src.config import config
from src.utils.i18n import t



logger = logging.getLogger("steamlibmgr.backup_manager")

class BackupManager:
    """
    Manages creation and rotation of file backups.

    This class creates timestamped copies of files and automatically removes
    old backups when the configured maximum number is exceeded.
    """

    def __init__(self, backup_dir: Optional[Path] = None):
        """
        Initializes the BackupManager.

        Args:
            backup_dir (Optional[Path]): Custom directory for storing backups.
                                         If None, backups will be created in the same
                                         directory as the original file.
        """
        self.backup_dir = backup_dir

    def create_backup(self, file_path: Path) -> Optional[Path]:
        """
        Creates a timestamped backup of a file.

        The backup is saved with a timestamp in the filename (e.g., localconfig_20240128_143022.vdf).
        After creating the backup, old backups are automatically rotated based on the MAX_BACKUPS setting.

        If no backup_dir was specified in __init__, the backup is created in the same directory
        as the original file.

        Args:
            file_path (Path): Path to the file to back up.

        Returns:
            Optional[Path]: Path to the created backup file, or None if the operation failed
                           (e.g., source file doesn't exist).
        """
        if not file_path.exists():
            return None

        # Use Unix timestamp (seconds since 1970) - short and unique
        timestamp = str(int(datetime.now().timestamp()))
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"

        # Use specified backup_dir or same directory as original file
        target_dir = self.backup_dir if self.backup_dir else file_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        backup_path = target_dir / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            logger.info(t('logs.backup.created', name=backup_name))

            # Rotate old backups
            self._rotate_backups(file_path)

            return backup_path
        except OSError as backup_error:
            logger.error(t('logs.backup.failed', error=str(backup_error)))
            return None

    def _rotate_backups(self, file_path: Path):
        """
        Removes old backups exceeding the MAX_BACKUPS limit.

        This method finds all backups for a given file (by matching the filename pattern)
        and deletes the oldest ones if the total count exceeds the configured limit.

        Args:
            file_path (Path): The original file path (used to match backup files).
        """
        # Use specified backup_dir or same directory as original file
        target_dir = self.backup_dir if self.backup_dir else file_path.parent
        pattern = str(target_dir / f"{file_path.stem}_*{file_path.suffix}")
        backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

        if len(backups) > config.MAX_BACKUPS:
            for old in backups[config.MAX_BACKUPS:]:
                try:
                    os.remove(old)
                    logger.info(t('logs.backup.rotated', name=Path(old).name))
                except OSError as delete_error:
                    logger.error(t('logs.backup.delete_error', name=Path(old).name, error=str(delete_error)))

    @staticmethod
    def create_rolling_backup(file_path: Path) -> Optional[str]:
        """
        Legacy static method for creating backups with default settings.

        This method provides backward compatibility for code that calls the static
        create_rolling_backup method. It creates a BackupManager instance with
        default settings and delegates to create_backup.

        Args:
            file_path (Path): Path to the file to back up.

        Returns:
            Optional[str]: String path to the created backup, or None if the operation failed.
        """
        manager = BackupManager()
        backup_path = manager.create_backup(file_path)
        return str(backup_path) if backup_path else None
