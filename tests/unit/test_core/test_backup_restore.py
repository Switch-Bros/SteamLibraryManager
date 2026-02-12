# tests/unit/test_core/test_backup_restore.py

"""Unit tests for BackupManager list_backups and restore_backup."""

import time
from pathlib import Path

class TestBackupManagerListBackups:
    """Tests for BackupManager.list_backups()."""

    def test_list_backups_returns_empty_for_no_backups(self, tmp_path: Path):
        """No backups exist yet — expect empty list."""
        from src.core.backup_manager import BackupManager

        original = tmp_path / "test.json"
        original.write_text("{}")

        manager = BackupManager(backup_dir=tmp_path)
        result = manager.list_backups(original)

        assert result == []

    def test_list_backups_returns_sorted_newest_first(self, tmp_path: Path):
        """Multiple backups should be returned newest-first by mtime."""
        from src.core.backup_manager import BackupManager

        original = tmp_path / "test.json"
        original.write_text("{}")

        manager = BackupManager(backup_dir=tmp_path)

        # Create backups with different timestamps
        backup1 = tmp_path / "test_1000000.json"
        backup1.write_text("old")

        backup2 = tmp_path / "test_2000000.json"
        backup2.write_text("new")

        # Ensure different mtime
        backup1.touch()
        time.sleep(0.05)
        backup2.touch()

        result = manager.list_backups(original)

        assert len(result) == 2
        assert result[0] == backup2  # newest first
        assert result[1] == backup1

    def test_list_backups_only_matches_same_stem(self, tmp_path: Path):
        """Backups for other files should not appear."""
        from src.core.backup_manager import BackupManager

        original = tmp_path / "test.json"
        original.write_text("{}")

        # Create a matching backup and a non-matching file
        matching = tmp_path / "test_1000000.json"
        matching.write_text("match")

        other = tmp_path / "other_1000000.json"
        other.write_text("no match")

        manager = BackupManager(backup_dir=tmp_path)
        result = manager.list_backups(original)

        assert len(result) == 1
        assert result[0] == matching


class TestBackupManagerRestoreBackup:
    """Tests for BackupManager.restore_backup()."""

    def test_restore_backup_copies_content(self, tmp_path: Path):
        """Restored file should have backup's content."""
        from src.core.backup_manager import BackupManager

        original = tmp_path / "test.json"
        original.write_text("original content")

        backup = tmp_path / "test_1000000.json"
        backup.write_text("backup content")

        manager = BackupManager(backup_dir=tmp_path)
        result = manager.restore_backup(backup, original)

        assert result is True
        assert original.read_text() == "backup content"

    def test_restore_backup_creates_safety_backup(self, tmp_path: Path):
        """A safety backup of the current state should be created before restore."""
        from src.core.backup_manager import BackupManager

        original = tmp_path / "test.json"
        original.write_text("current state")

        backup = tmp_path / "test_1000000.json"
        backup.write_text("old state")

        manager = BackupManager(backup_dir=tmp_path)
        manager.restore_backup(backup, original)

        # Should have at least 2 files matching test_*.json (the source backup + safety backup)
        backups = manager.list_backups(original)
        assert len(backups) >= 2

    def test_restore_backup_nonexistent_backup_returns_false(self, tmp_path: Path):
        """Restoring from a nonexistent backup should fail gracefully."""
        from src.core.backup_manager import BackupManager

        original = tmp_path / "test.json"
        original.write_text("content")

        fake_backup = tmp_path / "test_nonexistent.json"

        manager = BackupManager(backup_dir=tmp_path)
        result = manager.restore_backup(fake_backup, original)

        assert result is False
        assert original.read_text() == "content"  # unchanged

    def test_restore_backup_to_nonexistent_original(self, tmp_path: Path):
        """Restoring when the original doesn't exist should still work."""
        from src.core.backup_manager import BackupManager

        original = tmp_path / "new_file.json"
        backup = tmp_path / "new_file_1000000.json"
        backup.write_text("restored content")

        manager = BackupManager(backup_dir=tmp_path)
        result = manager.restore_backup(backup, original)

        assert result is True
        assert original.read_text() == "restored content"
