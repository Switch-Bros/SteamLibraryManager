# tests/unit/test_core/test_cloud_storage_parser.py

"""Unit tests for CloudStorageParser."""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch


class TestCloudStorageParser:
    """Tests for src/core/cloud_storage_parser.py"""

    def test_load_collections(self, mock_cloud_storage_file):
        """Test loading collections from cloud storage file."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        result = parser.load()

        assert result is True
        assert len(parser.collections) == 1
        assert parser.collections[0]["name"] == "Action"

    def test_get_app_categories(self, mock_cloud_storage_file):
        """Test getting categories for a specific app."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        categories = parser.get_app_categories("440")

        assert "Action" in categories
        assert isinstance(categories, list)

    def test_add_app_category(self, mock_cloud_storage_file):
        """Test adding a category to an app."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        parser.add_app_category("570", "RPG")

        categories = parser.get_app_categories("570")
        assert "RPG" in categories
        assert parser.modified is True

    def test_get_duplicate_groups_no_duplicates(self, mock_cloud_storage_file):
        """Test that no duplicates returns empty dict."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        result = parser.get_duplicate_groups()

        assert result == {}

    def test_get_duplicate_groups_with_duplicates(self):
        """Test detection of duplicate collection names."""
        from src.core.cloud_storage_parser import CloudStorageParser

        parser = CloudStorageParser("/tmp/fake", "999")
        parser.collections = [
            {"id": "from-tag-RPG", "name": "RPG", "added": [100, 200]},
            {"id": "from-tag-RPG-2", "name": "RPG", "added": [300]},
            {"id": "from-tag-Action", "name": "Action", "added": [100]},
        ]

        result = parser.get_duplicate_groups()

        assert "RPG" in result
        assert len(result["RPG"]) == 2
        assert "Action" not in result

    def test_get_duplicate_groups_empty_collections(self):
        """Test with empty collections list."""
        from src.core.cloud_storage_parser import CloudStorageParser

        parser = CloudStorageParser("/tmp/fake", "999")
        parser.collections = []

        result = parser.get_duplicate_groups()

        assert result == {}


class TestCloudStorageConflictDetection:
    """Tests for external change detection and conflict handling."""

    def test_has_external_changes_true(self, mock_cloud_storage_file):
        """Detect external modifications after load by comparing mtime."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        # Simulate external modification by touching the file with a future mtime
        cloud_file = Path(parser.cloud_storage_path)
        future_time = time.time() + 10
        os.utime(cloud_file, (future_time, future_time))

        assert parser.has_external_changes() is True

    def test_has_external_changes_false(self, mock_cloud_storage_file):
        """No external changes when file is untouched since load."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        assert parser.has_external_changes() is False

    def test_has_external_changes_no_file(self):
        """Non-existent file should return False (not crash)."""
        from src.core.cloud_storage_parser import CloudStorageParser

        parser = CloudStorageParser("/tmp/nonexistent", "999")

        assert parser.has_external_changes() is False

    def test_save_with_conflict_sets_flag(self, mock_cloud_storage_file):
        """Saving after external change should set had_conflict flag."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        # Simulate external modification
        cloud_file = Path(parser.cloud_storage_path)
        future_time = time.time() + 10
        os.utime(cloud_file, (future_time, future_time))

        parser.save()

        assert parser.had_conflict is True

    def test_save_without_conflict_clears_flag(self, mock_cloud_storage_file):
        """Saving without external changes should not set had_conflict."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        parser.save()

        assert parser.had_conflict is False

    @patch("src.core.cloud_storage_parser.BackupManager")
    def test_save_creates_backup(self, mock_backup_cls, mock_cloud_storage_file):
        """Save should create a backup of the existing file."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        parser.save()

        mock_backup_cls.return_value.create_backup.assert_called_once()


class TestCloudStorageVirtualCategories:
    """Tests that virtual and special categories are handled correctly on save."""

    def test_virtual_categories_not_saved(self, mock_cloud_storage_file):
        """Virtual UI categories should be stripped during save."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        # Inject virtual categories that should NOT be persisted
        virtual_names = list(CloudStorageParser._get_virtual_categories())
        for name in virtual_names:
            parser.collections.append({"id": f"from-tag-{name}", "name": name, "added": [999], "removed": []})

        parser.save()

        # Reload and verify virtual categories were NOT written
        parser2 = CloudStorageParser(str(steam_path), user_id)
        parser2.load()
        saved_names = {c["name"] for c in parser2.collections}

        for name in virtual_names:
            assert name not in saved_names, f"Virtual category '{name}' was saved!"

    def test_special_collections_use_steam_ids(self, mock_cloud_storage_file):
        """Favorites and Hidden should be saved with Steam-internal IDs."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        # Add special collections with localised names
        special_ids = CloudStorageParser._get_special_collection_ids()
        for display_name, steam_id in special_ids.items():
            parser.collections.append(
                {"id": f"from-tag-{display_name}", "name": display_name, "added": [440], "removed": []}
            )

        parser.save()

        # Read raw JSON and verify Steam-internal keys
        with open(parser.cloud_storage_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        saved_keys = [item[0] for item in raw_data if isinstance(item, list) and len(item) == 2]

        for steam_id in special_ids.values():
            expected_key = f"user-collections.{steam_id}"
            assert expected_key in saved_keys, f"Special collection key '{expected_key}' not found"

    def test_empty_special_collections_not_saved(self, mock_cloud_storage_file):
        """Empty favorites/hidden should be omitted from save."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        # Add empty special collections
        special_ids = CloudStorageParser._get_special_collection_ids()
        for display_name in special_ids:
            parser.collections.append(
                {"id": f"from-tag-{display_name}", "name": display_name, "added": [], "removed": []}
            )

        parser.save()

        # Reload — empty special collections should not appear
        parser2 = CloudStorageParser(str(steam_path), user_id)
        parser2.load()
        saved_names = {c["name"] for c in parser2.collections}

        for display_name in special_ids:
            assert display_name not in saved_names, f"Empty special collection '{display_name}' was saved!"


class TestCloudStorageFilterSpec:
    """Tests for dynamic collection filterSpec preservation."""

    def test_filterspec_preserved_on_save(self, mock_cloud_storage_file):
        """Dynamic collection filterSpec should survive save/load round-trip."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        # Add a dynamic collection with filterSpec
        dynamic_collection = {
            "id": "uc-dynamic-123",
            "name": "Linux Games",
            "added": [440, 570],
            "removed": [],
            "filterSpec": {"nOSType": "linux"},
        }
        parser.collections.append(dynamic_collection)

        parser.save()

        # Reload and verify filterSpec survived
        parser2 = CloudStorageParser(str(steam_path), user_id)
        parser2.load()

        linux_coll = next((c for c in parser2.collections if c["name"] == "Linux Games"), None)
        assert linux_coll is not None, "Dynamic collection lost during save"
        assert "filterSpec" in linux_coll, "filterSpec was stripped during save"
        assert linux_coll["filterSpec"]["nOSType"] == "linux"


class TestCloudStorageCorruptedData:
    """Tests for resilience against corrupted or malformed data."""

    def test_corrupted_json_returns_false(self, tmp_path):
        """Corrupted JSON file should fail gracefully."""
        from src.core.cloud_storage_parser import CloudStorageParser

        user_id = "12345678"
        cloud_dir = tmp_path / "userdata" / user_id / "config" / "cloudstorage"
        cloud_dir.mkdir(parents=True)
        cloud_file = cloud_dir / "cloud-storage-namespace-1.json"
        cloud_file.write_text("{{{INVALID JSON!!!")

        parser = CloudStorageParser(str(tmp_path), user_id)
        result = parser.load()

        assert result is False
        assert parser.collections == []

    def test_non_list_data_returns_false(self, tmp_path):
        """Root-level non-list JSON should fail gracefully."""
        from src.core.cloud_storage_parser import CloudStorageParser

        user_id = "12345678"
        cloud_dir = tmp_path / "userdata" / user_id / "config" / "cloudstorage"
        cloud_dir.mkdir(parents=True)
        cloud_file = cloud_dir / "cloud-storage-namespace-1.json"
        cloud_file.write_text('{"not": "a list"}')

        parser = CloudStorageParser(str(tmp_path), user_id)
        result = parser.load()

        assert result is False

    def test_bare_timestamp_in_added_field(self, mock_cloud_storage_file):
        """Migrated collection with 'added': 0 (bare timestamp) should not crash."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        parser.load()

        # Inject a collection with bare int instead of list for 'added'
        parser.collections.append({"id": "from-tag-Broken", "name": "Broken", "added": 0, "removed": []})

        # get_app_categories should handle this without crashing
        categories = parser.get_app_categories("440")
        assert isinstance(categories, list)

        # Save should also handle this gracefully
        parser.save()

    def test_to_app_id_int_invalid_values(self):
        """Invalid app_id values should return None."""
        from src.core.cloud_storage_parser import CloudStorageParser

        assert CloudStorageParser._to_app_id_int("abc") is None
        assert CloudStorageParser._to_app_id_int("") is None
        assert CloudStorageParser._to_app_id_int(None) is None
        assert CloudStorageParser._to_app_id_int(440) == 440
        assert CloudStorageParser._to_app_id_int("570") == 570
