#
# steam_library_manager/core/backup_manager.py
# File backup creation with automatic rotation and limit enforcement
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
    """Manages file backups with automatic rotation."""

    def __init__(self, backup_dir=None):
        # init manager
        self.backup_dir = backup_dir

    def create_backup(self, file_path):
        # create timestamped backup of file
        if not file_path.exists():
            return None

        # use Unix timestamp - short and unique
        ts = str(int(datetime.now().timestamp()))
        backup_name = "%s_%s%s" % (file_path.stem, ts, file_path.suffix)

        # use specified dir or same dir as original
        target_dir = self.backup_dir if self.backup_dir else file_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        backup_path = target_dir / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            logger.info(t("logs.backup.created", name=backup_name))

            # rotate old backups
            self._rotate_backups(file_path)

            return backup_path
        except OSError as e:
            logger.error(t("logs.backup.failed", error=str(e)))
            return None

    def _rotate_backups(self, file_path):
        # remove old backups exceeding limit
        target_dir = self.backup_dir if self.backup_dir else file_path.parent
        pattern = str(target_dir / ("%s_*%s" % (file_path.stem, file_path.suffix)))
        backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

        if len(backups) > config.MAX_BACKUPS:
            for old in backups[config.MAX_BACKUPS :]:
                try:
                    os.remove(old)
                    logger.info(t("logs.backup.rotated", name=Path(old).name))
                except OSError as e:
                    logger.error(t("logs.backup.delete_error", name=Path(old).name, error=str(e)))

    def list_backups(self, file_path):
        # list all backups for file, newest first
        target_dir = self.backup_dir if self.backup_dir else file_path.parent
        pattern = str(target_dir / ("%s_*%s" % (file_path.stem, file_path.suffix)))
        backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        return [Path(b) for b in backups]

    def restore_backup(self, backup_path, original_path):
        # restore backup to original location
        if not backup_path.exists():
            logger.error(t("logs.backup.restore_failed", error="Backup file not found"))
            return False

        try:
            # safety backup of current state
            if original_path.exists():
                self.create_backup(original_path)

            shutil.copy2(backup_path, original_path)
            logger.info(t("logs.backup.restore_success", name=backup_path.name))
            return True
        except OSError as e:
            logger.error(t("logs.backup.restore_failed", error=str(e)))
            return False

    @staticmethod
    def create_rolling_backup(file_path):
        # legacy static method for backwards compat
        mgr = BackupManager()
        backup_path = mgr.create_backup(file_path)
        return str(backup_path) if backup_path else None
