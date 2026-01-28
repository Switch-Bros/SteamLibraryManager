"""
Backup Manager - Rolling Backups
Handles file backups with automatic rotation (keeping only the newest N files).
"""
import shutil
import glob
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from src.config import config
from src.utils.i18n import t


class BackupManager:
    """Manager for creating and rotating backups of configuration files."""

    def __init__(self, backup_dir: Optional[Path] = None):
        """
        Initialize BackupManager.

        Args:
            backup_dir: Custom backup directory (optional).
        """
        self.backup_dir = backup_dir or (config.DATA_DIR / 'backups')
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, file_path: Path) -> Optional[Path]:
        """
        Create backup of a file with timestamp.

        Args:
            file_path: Path to file to back up.

        Returns:
            Path to backup file, or None if failed.
        """
        if not file_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            print(t('logs.backup.created', name=backup_name))

            # Rotate old backups
            self._rotate_backups(file_path)

            return backup_path
        except OSError as backup_error:
            print(t('logs.backup.failed', error=str(backup_error)))
            return None

    def _rotate_backups(self, file_path: Path):
        """Remove old backups exceeding MAX_BACKUPS limit."""
        pattern = str(self.backup_dir / f"{file_path.stem}_*{file_path.suffix}")
        backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

        if len(backups) > config.MAX_BACKUPS:
            for old in backups[config.MAX_BACKUPS:]:
                try:
                    os.remove(old)
                    print(t('logs.backup.rotated', name=Path(old).name))
                except OSError as delete_error:
                    print(t('logs.backup.delete_error', name=Path(old).name, error=str(delete_error)))

    @staticmethod
    def create_rolling_backup(file_path: Path) -> Optional[str]:
        """
        Legacy method for backward compatibility.
        Creates backup using default config directory.

        Args:
            file_path: Path to file to back up.

        Returns:
            String path to backup, or None if failed.
        """
        manager = BackupManager()
        backup_path = manager.create_backup(file_path)
        return str(backup_path) if backup_path else None