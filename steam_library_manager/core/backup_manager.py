#
# steam_library_manager/core/backup_manager.py
# Timestamped file backups with automatic rotation
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import shutil
import glob
import os
from pathlib import Path
from datetime import datetime
from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.backup_manager")

__all__ = ["BackupManager"]


class BackupManager:
    """Manages creation and rotation of file backups."""

    def __init__(self, backup_dir: Path | None = None):
        """If backup_dir is None, backups go next to the original file."""
        self.backup_dir = backup_dir

    def create_backup(self, file_path: Path) -> Path | None:
        """Create a timestamped backup, then rotate old ones."""
        if not file_path.exists():
            return None

        timestamp = str(int(datetime.now().timestamp()))
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"

        target_dir = self.backup_dir if self.backup_dir else file_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        backup_path = target_dir / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            logger.info(t("logs.backup.created", name=backup_name))

            self._rotate_backups(file_path)

            return backup_path
        except OSError as backup_error:
            logger.error(t("logs.backup.failed", error=str(backup_error)))
            return None

    def _rotate_backups(self, file_path: Path):
        target_dir = self.backup_dir if self.backup_dir else file_path.parent
        pattern = str(target_dir / f"{file_path.stem}_*{file_path.suffix}")
        backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

        if len(backups) > config.MAX_BACKUPS:
            for old in backups[config.MAX_BACKUPS :]:
                try:
                    os.remove(old)
                    logger.info(t("logs.backup.rotated", name=Path(old).name))
                except OSError as delete_error:
                    logger.error(t("logs.backup.delete_error", name=Path(old).name, error=str(delete_error)))

    def list_backups(self, file_path: Path) -> list[Path]:
        """All backups for a file, sorted newest first."""
        target_dir = self.backup_dir if self.backup_dir else file_path.parent
        pattern = str(target_dir / f"{file_path.stem}_*{file_path.suffix}")
        backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        return [Path(b) for b in backups]

    def restore_backup(self, backup_path: Path, original_path: Path) -> bool:
        """Restore a backup, creating a safety copy of the current file first."""
        if not backup_path.exists():
            logger.error(t("logs.backup.restore_failed", error="Backup file not found"))
            return False

        try:
            if original_path.exists():
                self.create_backup(original_path)

            shutil.copy2(backup_path, original_path)
            logger.info(t("logs.backup.restore_success", name=backup_path.name))
            return True
        except OSError as e:
            logger.error(t("logs.backup.restore_failed", error=str(e)))
            return False

    @staticmethod
    def create_rolling_backup(file_path: Path) -> str | None:
        """Legacy convenience wrapper around create_backup()."""
        manager = BackupManager()
        backup_path = manager.create_backup(file_path)
        return str(backup_path) if backup_path else None
