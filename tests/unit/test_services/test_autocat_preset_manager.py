"""Unit tests for AutoCatPresetManager."""

import json

import pytest

from src.services.autocat_preset_manager import AutoCatPreset, AutoCatPresetManager


class TestAutoCatPreset:
    """Tests for the AutoCatPreset dataclass."""

    def test_preset_creation(self) -> None:
        """Test creating a preset with all fields."""
        preset = AutoCatPreset(
            name="Test Preset",
            methods=("tags", "publisher"),
            tags_count=10,
            ignore_common=False,
            curator_url="https://store.steampowered.com/curator/123/",
            curator_recommendations=("recommended",),
        )
        assert preset.name == "Test Preset"
        assert preset.methods == ("tags", "publisher")
        assert preset.tags_count == 10
        assert preset.ignore_common is False
        assert preset.curator_url == "https://store.steampowered.com/curator/123/"
        assert preset.curator_recommendations == ("recommended",)

    def test_preset_defaults(self) -> None:
        """Test preset default values."""
        preset = AutoCatPreset(name="Minimal")
        assert preset.methods == ()
        assert preset.tags_count == 13
        assert preset.ignore_common is True
        assert preset.curator_url is None
        assert preset.curator_recommendations is None

    def test_preset_is_frozen(self) -> None:
        """Test that preset is immutable."""
        preset = AutoCatPreset(name="Frozen")
        with pytest.raises(AttributeError):
            preset.name = "Changed"  # type: ignore[misc]


class TestAutoCatPresetManager:
    """Tests for CRUD operations on presets."""

    @pytest.fixture
    def tmp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        return tmp_path

    @pytest.fixture
    def manager(self, tmp_data_dir) -> AutoCatPresetManager:
        """Create a preset manager with temp directory."""
        return AutoCatPresetManager(data_dir=tmp_data_dir)

    def test_load_presets_empty_returns_empty(self, manager: AutoCatPresetManager) -> None:
        """Test loading presets when no file exists."""
        assert manager.load_presets() == []

    def test_save_and_load_preset(self, manager: AutoCatPresetManager) -> None:
        """Test saving and loading a single preset."""
        preset = AutoCatPreset(
            name="My Preset",
            methods=("tags", "genre"),
            tags_count=5,
        )
        manager.save_preset(preset)

        loaded = manager.load_presets()
        assert len(loaded) == 1
        assert loaded[0].name == "My Preset"
        assert loaded[0].methods == ("tags", "genre")
        assert loaded[0].tags_count == 5

    def test_save_preset_overwrites_existing(self, manager: AutoCatPresetManager) -> None:
        """Test that saving a preset with the same name overwrites it."""
        preset1 = AutoCatPreset(name="Test", methods=("tags",), tags_count=5)
        preset2 = AutoCatPreset(name="Test", methods=("genre",), tags_count=10)

        manager.save_preset(preset1)
        manager.save_preset(preset2)

        loaded = manager.load_presets()
        assert len(loaded) == 1
        assert loaded[0].methods == ("genre",)
        assert loaded[0].tags_count == 10

    def test_save_multiple_presets(self, manager: AutoCatPresetManager) -> None:
        """Test saving multiple different presets."""
        manager.save_preset(AutoCatPreset(name="A", methods=("tags",)))
        manager.save_preset(AutoCatPreset(name="B", methods=("genre",)))
        manager.save_preset(AutoCatPreset(name="C", methods=("publisher",)))

        loaded = manager.load_presets()
        assert len(loaded) == 3
        names = {p.name for p in loaded}
        assert names == {"A", "B", "C"}

    def test_delete_preset_success(self, manager: AutoCatPresetManager) -> None:
        """Test deleting an existing preset."""
        manager.save_preset(AutoCatPreset(name="ToDelete", methods=("tags",)))
        assert manager.delete_preset("ToDelete") is True
        assert manager.load_presets() == []

    def test_delete_preset_not_found(self, manager: AutoCatPresetManager) -> None:
        """Test deleting a non-existent preset returns False."""
        assert manager.delete_preset("NonExistent") is False

    def test_delete_preset_keeps_others(self, manager: AutoCatPresetManager) -> None:
        """Test that deleting one preset does not affect others."""
        manager.save_preset(AutoCatPreset(name="Keep", methods=("tags",)))
        manager.save_preset(AutoCatPreset(name="Delete", methods=("genre",)))

        manager.delete_preset("Delete")

        loaded = manager.load_presets()
        assert len(loaded) == 1
        assert loaded[0].name == "Keep"

    def test_rename_preset_success(self, manager: AutoCatPresetManager) -> None:
        """Test renaming a preset."""
        manager.save_preset(AutoCatPreset(name="Old", methods=("tags",), tags_count=7))
        assert manager.rename_preset("Old", "New") is True

        loaded = manager.load_presets()
        assert len(loaded) == 1
        assert loaded[0].name == "New"
        assert loaded[0].methods == ("tags",)
        assert loaded[0].tags_count == 7

    def test_rename_preset_not_found(self, manager: AutoCatPresetManager) -> None:
        """Test renaming non-existent preset returns False."""
        assert manager.rename_preset("Ghost", "New") is False

    def test_load_corrupt_file_returns_empty(self, tmp_data_dir) -> None:
        """Test loading from corrupt JSON file returns empty list."""
        preset_file = tmp_data_dir / "autocat_presets.json"
        preset_file.write_text("not valid json!!!", encoding="utf-8")

        manager = AutoCatPresetManager(data_dir=tmp_data_dir)
        assert manager.load_presets() == []

    def test_load_malformed_preset_skips_entry(self, tmp_data_dir) -> None:
        """Test that malformed preset entries are skipped."""
        preset_file = tmp_data_dir / "autocat_presets.json"
        data = [
            {"name": "Good", "methods": ["tags"], "tags_count": 5},
            {"bad_key": "missing name field"},
        ]
        preset_file.write_text(json.dumps(data), encoding="utf-8")

        manager = AutoCatPresetManager(data_dir=tmp_data_dir)
        loaded = manager.load_presets()
        assert len(loaded) == 1
        assert loaded[0].name == "Good"

    def test_preset_with_curator_data(self, manager: AutoCatPresetManager) -> None:
        """Test saving and loading a preset with curator data."""
        preset = AutoCatPreset(
            name="Curator Test",
            methods=("curator", "tags"),
            curator_url="https://store.steampowered.com/curator/123/",
            curator_recommendations=("recommended", "informational"),
        )
        manager.save_preset(preset)

        loaded = manager.load_presets()
        assert len(loaded) == 1
        assert loaded[0].curator_url == "https://store.steampowered.com/curator/123/"
        assert loaded[0].curator_recommendations == ("recommended", "informational")

    def test_preset_json_format(self, manager: AutoCatPresetManager, tmp_data_dir) -> None:
        """Test that presets are written as proper JSON."""
        manager.save_preset(AutoCatPreset(name="JSON Test", methods=("tags", "genre")))

        file_path = tmp_data_dir / "autocat_presets.json"
        data = json.loads(file_path.read_text(encoding="utf-8"))

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "JSON Test"
        assert data[0]["methods"] == ["tags", "genre"]
