"""
Backup Manager - Rolling Backups
Speichern als: src/core/backup_manager.py
"""
import shutil
import glob
import os
from pathlib import Path
from datetime import datetime
from src.config import config


class BackupManager:
    @staticmethod
    def create_rolling_backup(file_path: Path) -> str:
        if not file_path.exists(): return None

        backup_dir = config.DATA_DIR / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = backup_dir / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            print(f"✓ Backup created: {backup_name}")

            # Rotation
            pattern = str(backup_dir / f"{file_path.stem}_*{file_path.suffix}")
            backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

            if len(backups) > config.MAX_BACKUPS:
                for old in backups[config.MAX_BACKUPS:]:
                    try:
                        os.remove(old)
                    except:
                        pass
            return str(backup_path)
        except Exception as e:
            print(f"Backup failed: {e}")
            return None