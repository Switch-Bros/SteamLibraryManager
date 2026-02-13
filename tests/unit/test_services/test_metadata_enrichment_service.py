# tests/unit/test_services/test_metadata_enrichment_service.py

"""Tests for MetadataEnrichmentService."""

import json
from unittest.mock import MagicMock

from src.core.game import Game
from src.services.metadata_enrichment_service import MetadataEnrichmentService


class TestMetadataEnrichmentServiceInit:
    """Tests for MetadataEnrichmentService initialization."""

    def test_init_stores_references(self, tmp_path):
        """Test that init stores games dict and cache dir."""
        games = {"440": Game(app_id="440", name="TF2")}
        service = MetadataEnrichmentService(games, tmp_path)
        assert service._games is games
        assert service._cache_dir == tmp_path


class TestApplyAppinfoData:
    """Tests for apply_appinfo_data."""

    def test_applies_last_updated(self, tmp_path):
        """Test that last_updated timestamp is applied from appinfo data."""
        game = Game(app_id="440", name="TF2")
        games = {"440": game}
        service = MetadataEnrichmentService(games, tmp_path)

        appinfo_data = {"440": {"common": {"last_updated": 1700000000}}}
        service.apply_appinfo_data(appinfo_data)

        # Should have a non-empty date string
        assert game.last_updated != ""

    def test_skips_missing_game(self, tmp_path):
        """Test that appinfo data for unknown game is silently skipped."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)
        # Should not raise
        service.apply_appinfo_data({"999": {"common": {"last_updated": 123}}})

    def test_skips_missing_last_updated_key(self, tmp_path):
        """Test that entries without last_updated are skipped."""
        game = Game(app_id="440", name="TF2")
        games = {"440": game}
        service = MetadataEnrichmentService(games, tmp_path)

        appinfo_data = {"440": {"common": {"name": "TF2"}}}
        service.apply_appinfo_data(appinfo_data)

        assert game.last_updated == ""


class TestApplyMetadataOverrides:
    """Tests for apply_metadata_overrides."""

    def test_applies_binary_metadata(self, tmp_path):
        """Test that binary appinfo metadata is applied."""
        game = Game(app_id="440", name="App 440")
        games = {"440": game}
        service = MetadataEnrichmentService(games, tmp_path)

        appinfo_manager = MagicMock()
        appinfo_manager.steam_apps = {440: {}}
        appinfo_manager.modifications = {}
        appinfo_manager.get_app_metadata.return_value = {
            "name": "Team Fortress 2",
            "developer": "Valve",
            "publisher": "Valve",
        }

        service.apply_metadata_overrides(appinfo_manager)

        assert game.name == "Team Fortress 2"
        assert game.developer == "Valve"

    def test_applies_custom_overrides(self, tmp_path):
        """Test that custom user overrides are applied."""
        game = Game(app_id="440", name="TF2")
        games = {"440": game}
        service = MetadataEnrichmentService(games, tmp_path)

        appinfo_manager = MagicMock()
        appinfo_manager.steam_apps = {440: {}}
        appinfo_manager.modifications = {"440": {"modified": {"name": "TF2 Custom", "developer": "Custom Dev"}}}
        appinfo_manager.get_app_metadata.return_value = {}

        service.apply_metadata_overrides(appinfo_manager)

        assert game.name == "TF2 Custom"
        assert game.name_overridden is True
        assert game.developer == "Custom Dev"

    def test_custom_override_does_not_overwrite_empty_app(self, tmp_path):
        """Test that overrides for missing games are skipped."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        appinfo_manager = MagicMock()
        appinfo_manager.steam_apps = {}
        appinfo_manager.modifications = {"999": {"modified": {"name": "Ghost Game"}}}
        appinfo_manager.get_app_metadata.return_value = {}

        # Should not raise
        service.apply_metadata_overrides(appinfo_manager)


class TestGetCachedName:
    """Tests for _get_cached_name."""

    def test_returns_cached_name(self, tmp_path):
        """Test that cached name is returned from store_data cache."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        cache_dir = tmp_path / "store_data"
        cache_dir.mkdir()
        cache_file = cache_dir / "440.json"
        cache_file.write_text(json.dumps({"name": "Team Fortress 2"}))

        assert service._get_cached_name("440") == "Team Fortress 2"

    def test_returns_none_for_missing_cache(self, tmp_path):
        """Test that None is returned when cache file doesn't exist."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)
        assert service._get_cached_name("440") is None

    def test_returns_none_for_corrupt_cache(self, tmp_path):
        """Test that None is returned for corrupted cache file."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        cache_dir = tmp_path / "store_data"
        cache_dir.mkdir()
        cache_file = cache_dir / "440.json"
        cache_file.write_text("not valid json{{{")

        assert service._get_cached_name("440") is None
