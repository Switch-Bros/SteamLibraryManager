# tests/unit/test_core/test_cloud_storage_parser.py

"""Unit tests for CloudStorageParser."""


class TestCloudStorageParser:
    """Tests for src/core/cloud_storage_parser.py"""

    def test_load_collections(self, mock_cloud_storage_file):
        """Test loading collections from cloud storage file."""
        from src.core.cloud_storage_parser import CloudStorageParser

        steam_path, user_id = mock_cloud_storage_file
        parser = CloudStorageParser(str(steam_path), user_id)
        result = parser.load()

        assert result == True
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
        assert parser.modified == True

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
