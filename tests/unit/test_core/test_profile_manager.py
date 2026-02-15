# tests/unit/test_core/test_profile_manager.py

"""Tests for Profile dataclass, ProfileManager, and serialization helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.profile_manager import (
    Profile,
    ProfileManager,
    _deserialize_profile,
    _sanitize_filename,
    _serialize_profile,
)
from src.services.filter_service import ALL_PLATFORM_KEYS, ALL_TYPE_KEYS

# ---------------------------------------------------------------------------
# Profile Dataclass
# ---------------------------------------------------------------------------


class TestProfileDataclass:
    """Tests for the frozen Profile dataclass."""

    def test_profile_creation_defaults_returns_valid_profile(self) -> None:
        """Default Profile should have sensible defaults for all fields."""
        p = Profile(name="Test")
        assert p.name == "Test"
        assert p.collections == ()
        assert p.tags_per_game == 13
        assert p.ignore_common_tags is True
        assert p.filter_enabled_types == ALL_TYPE_KEYS
        assert p.filter_enabled_platforms == ALL_PLATFORM_KEYS
        assert p.filter_active_statuses == frozenset()
        assert p.view_mode == "details"
        assert p.created_at == 0.0

    def test_profile_frozen_mutation_raises_error(self) -> None:
        """Frozen dataclass should prevent attribute mutation."""
        p = Profile(name="Immutable")
        with pytest.raises(AttributeError):
            p.name = "Changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Serialization Roundtrip
# ---------------------------------------------------------------------------


class TestSerialization:
    """Tests for _serialize_profile and _deserialize_profile."""

    def test_serialize_deserialize_roundtrip_preserves_data(self) -> None:
        """A roundtrip through serialize/deserialize should preserve all fields."""
        original = Profile(
            name="Full Profile",
            collections=({"id": "1", "name": "Action"},),
            autocat_methods=("tags", "genre"),
            tags_per_game=5,
            ignore_common_tags=False,
            filter_enabled_types=frozenset({"games", "dlcs"}),
            filter_enabled_platforms=frozenset({"linux"}),
            filter_active_statuses=frozenset({"installed"}),
            view_mode="grid",
            created_at=1700000000.0,
        )
        data = _serialize_profile(original)
        restored = _deserialize_profile(data)

        assert restored.name == original.name
        assert restored.collections == original.collections
        assert restored.autocat_methods == original.autocat_methods
        assert restored.tags_per_game == original.tags_per_game
        assert restored.ignore_common_tags == original.ignore_common_tags
        assert restored.filter_enabled_types == original.filter_enabled_types
        assert restored.filter_enabled_platforms == original.filter_enabled_platforms
        assert restored.filter_active_statuses == original.filter_active_statuses
        assert restored.view_mode == original.view_mode
        assert restored.created_at == original.created_at

    def test_deserialize_missing_optional_fields_uses_defaults(self) -> None:
        """Missing optional fields should fall back to Profile defaults."""
        data = {"name": "Minimal"}
        profile = _deserialize_profile(data)
        assert profile.name == "Minimal"
        assert profile.collections == ()
        assert profile.tags_per_game == 13
        assert profile.filter_enabled_types == ALL_TYPE_KEYS

    def test_deserialize_missing_name_raises_key_error(self) -> None:
        """A JSON dict without 'name' should raise KeyError."""
        with pytest.raises(KeyError, match="name"):
            _deserialize_profile({})


# ---------------------------------------------------------------------------
# save_profile
# ---------------------------------------------------------------------------


class TestSaveProfile:
    """Tests for ProfileManager.save_profile()."""

    def test_save_profile_valid_creates_json_file(self, tmp_path: Path) -> None:
        """Saving a valid profile should create a JSON file on disk."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        p = Profile(name="My Setup", created_at=100.0)
        result = mgr.save_profile(p)

        assert result.exists()
        assert result.suffix == ".json"

        with open(result, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["name"] == "My Setup"

    def test_save_profile_empty_name_raises_value_error(self, tmp_path: Path) -> None:
        """Saving a profile with an empty name should raise ValueError."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        with pytest.raises(ValueError, match="empty"):
            mgr.save_profile(Profile(name=""))

    def test_save_profile_whitespace_name_raises_value_error(self, tmp_path: Path) -> None:
        """Saving a profile with a whitespace-only name should raise ValueError."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        with pytest.raises(ValueError, match="empty"):
            mgr.save_profile(Profile(name="   "))

    def test_save_profile_overwrites_existing(self, tmp_path: Path) -> None:
        """Saving a profile with the same name should overwrite the old file."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        mgr.save_profile(Profile(name="Dup", tags_per_game=5))
        mgr.save_profile(Profile(name="Dup", tags_per_game=10))

        loaded = mgr.load_profile("Dup")
        assert loaded.tags_per_game == 10


# ---------------------------------------------------------------------------
# load_profile
# ---------------------------------------------------------------------------


class TestLoadProfile:
    """Tests for ProfileManager.load_profile()."""

    def test_load_profile_existing_returns_profile(self, tmp_path: Path) -> None:
        """Loading a saved profile should return the correct Profile."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        mgr.save_profile(Profile(name="Loadable", view_mode="grid"))
        loaded = mgr.load_profile("Loadable")
        assert loaded.name == "Loadable"
        assert loaded.view_mode == "grid"

    def test_load_profile_nonexistent_raises_file_not_found(self, tmp_path: Path) -> None:
        """Loading a non-existent profile should raise FileNotFoundError."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.load_profile("Ghost")


# ---------------------------------------------------------------------------
# delete_profile
# ---------------------------------------------------------------------------


class TestDeleteProfile:
    """Tests for ProfileManager.delete_profile()."""

    def test_delete_profile_existing_returns_true(self, tmp_path: Path) -> None:
        """Deleting an existing profile should return True."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        mgr.save_profile(Profile(name="ToDelete"))
        assert mgr.delete_profile("ToDelete") is True
        assert not list(tmp_path.glob("*.json"))

    def test_delete_profile_nonexistent_returns_false(self, tmp_path: Path) -> None:
        """Deleting a non-existent profile should return False."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        assert mgr.delete_profile("Nothing") is False


# ---------------------------------------------------------------------------
# list_profiles
# ---------------------------------------------------------------------------


class TestListProfiles:
    """Tests for ProfileManager.list_profiles()."""

    def test_list_profiles_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        """An empty profiles directory should return an empty list."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        assert mgr.list_profiles() == []

    def test_list_profiles_multiple_returns_sorted(self, tmp_path: Path) -> None:
        """Multiple profiles should be returned sorted by created_at (newest first)."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        mgr.save_profile(Profile(name="Old", created_at=100.0))
        mgr.save_profile(Profile(name="New", created_at=200.0))
        mgr.save_profile(Profile(name="Mid", created_at=150.0))

        result = mgr.list_profiles()
        assert len(result) == 3
        names = [name for name, _ in result]
        assert names == ["New", "Mid", "Old"]


# ---------------------------------------------------------------------------
# rename_profile
# ---------------------------------------------------------------------------


class TestRenameProfile:
    """Tests for ProfileManager.rename_profile()."""

    def test_rename_profile_valid_renames_file(self, tmp_path: Path) -> None:
        """Renaming should create a new file and delete the old one."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        mgr.save_profile(Profile(name="Original", created_at=42.0))
        result = mgr.rename_profile("Original", "Renamed")

        assert result is True
        loaded = mgr.load_profile("Renamed")
        assert loaded.name == "Renamed"
        assert loaded.created_at == 42.0

        with pytest.raises(FileNotFoundError):
            mgr.load_profile("Original")

    def test_rename_profile_nonexistent_returns_false(self, tmp_path: Path) -> None:
        """Renaming a non-existent profile should return False."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        assert mgr.rename_profile("Ghost", "New") is False

    def test_rename_profile_empty_name_raises_value_error(self, tmp_path: Path) -> None:
        """Renaming to an empty name should raise ValueError."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        mgr.save_profile(Profile(name="Valid"))
        with pytest.raises(ValueError, match="empty"):
            mgr.rename_profile("Valid", "")


# ---------------------------------------------------------------------------
# export / import
# ---------------------------------------------------------------------------


class TestExportImport:
    """Tests for ProfileManager export and import operations."""

    def test_export_profile_copies_to_target(self, tmp_path: Path) -> None:
        """Exporting should copy the profile JSON to the target path."""
        profiles_dir = tmp_path / "profiles"
        export_dir = tmp_path / "export"
        export_dir.mkdir()
        target = export_dir / "exported.json"

        mgr = ProfileManager(profiles_dir=profiles_dir)
        mgr.save_profile(Profile(name="Exportable", view_mode="grid"))
        success = mgr.export_profile("Exportable", target)

        assert success is True
        assert target.exists()

        with open(target, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["name"] == "Exportable"
        assert data["view_mode"] == "grid"

    def test_export_nonexistent_returns_false(self, tmp_path: Path) -> None:
        """Exporting a non-existent profile should return False."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        assert mgr.export_profile("Ghost", tmp_path / "out.json") is False

    def test_import_profile_valid_creates_profile(self, tmp_path: Path) -> None:
        """Importing a valid JSON file should save and return the profile."""
        profiles_dir = tmp_path / "profiles"
        source = tmp_path / "incoming.json"

        data = {"name": "Imported", "view_mode": "list", "created_at": 500.0}
        with open(source, "w", encoding="utf-8") as fh:
            json.dump(data, fh)

        mgr = ProfileManager(profiles_dir=profiles_dir)
        profile = mgr.import_profile(source)

        assert profile.name == "Imported"
        assert profile.view_mode == "list"

        # Verify it was saved locally
        loaded = mgr.load_profile("Imported")
        assert loaded.name == "Imported"

    def test_import_profile_invalid_json_raises_error(self, tmp_path: Path) -> None:
        """Importing a malformed JSON file should raise JSONDecodeError."""
        source = tmp_path / "bad.json"
        source.write_text("{invalid json", encoding="utf-8")

        mgr = ProfileManager(profiles_dir=tmp_path)
        with pytest.raises(json.JSONDecodeError):
            mgr.import_profile(source)

    def test_import_profile_missing_name_raises_key_error(self, tmp_path: Path) -> None:
        """Importing a JSON without 'name' should raise KeyError."""
        source = tmp_path / "noname.json"
        with open(source, "w", encoding="utf-8") as fh:
            json.dump({"view_mode": "details"}, fh)

        mgr = ProfileManager(profiles_dir=tmp_path)
        with pytest.raises(KeyError, match="name"):
            mgr.import_profile(source)

    def test_import_profile_nonexistent_source_raises_error(self, tmp_path: Path) -> None:
        """Importing from a non-existent file should raise FileNotFoundError."""
        mgr = ProfileManager(profiles_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.import_profile(tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# _sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    """Tests for the _sanitize_filename helper."""

    def test_sanitize_filename_special_chars_returns_safe(self) -> None:
        """Special characters should be replaced with underscores."""
        assert _sanitize_filename("My/Profile:v2!") == "My_Profile_v2_"

    def test_sanitize_filename_normal_preserved(self) -> None:
        """Normal alphanumeric names should be preserved."""
        assert _sanitize_filename("Action Games 2026") == "Action Games 2026"

    def test_sanitize_filename_spaces_preserved(self) -> None:
        """Spaces should be preserved in the sanitized name."""
        assert _sanitize_filename("My Great Profile") == "My Great Profile"

    def test_sanitize_filename_hyphens_preserved(self) -> None:
        """Hyphens should be preserved."""
        assert _sanitize_filename("setup-v2") == "setup-v2"
