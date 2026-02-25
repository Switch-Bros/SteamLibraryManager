# tests/unit/test_services/test_metadata_enrichment_service.py

"""Tests for MetadataEnrichmentService."""

import json
from unittest.mock import MagicMock

from src.core.game import Game
from src.services.enrichment.metadata_enrichment_service import MetadataEnrichmentService


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


class TestDiscoverFromDbLookup:
    """Tests for discover_missing_games with db_type_lookup."""

    def test_discover_from_db_lookup(self, tmp_path):
        """DB-based discovery adds games with matching discoverable types."""
        games: dict[str, Game] = {"440": Game(app_id="440", name="TF2")}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = ["440", "570", "730"]

        appinfo = MagicMock()

        db_lookup = {
            "570": ("game", "Dota 2"),
            "730": ("game", "Counter-Strike 2"),
        }

        count = service.discover_missing_games(
            localconfig,
            appinfo,
            db_type_lookup=db_lookup,
        )

        assert count == 2
        assert "570" in games
        assert games["570"].name == "Dota 2"
        assert "730" in games
        # Should NOT call appinfo_manager.get_app_metadata
        appinfo.get_app_metadata.assert_not_called()

    def test_discover_from_db_filters_non_discoverable(self, tmp_path):
        """DB-based discovery skips DLC, config, and other non-discoverable types."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = ["100", "200", "300"]

        appinfo = MagicMock()

        db_lookup = {
            "100": ("dlc", "Some DLC"),
            "200": ("config", "Some Config"),
            "300": ("game", "Real Game"),
        }

        count = service.discover_missing_games(
            localconfig,
            appinfo,
            db_type_lookup=db_lookup,
        )

        assert count == 1
        assert "300" in games
        assert "100" not in games
        assert "200" not in games


class TestDiscoverFallbackToAppinfo:
    """Tests for discover_missing_games fallback when ID is not in DB."""

    def test_falls_back_to_appinfo_for_unknown_db_ids(self, tmp_path):
        """AppIDs not in db_type_lookup are resolved via appinfo_manager."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = []

        appinfo = MagicMock()
        appinfo.appinfo = True  # Simulate already loaded
        appinfo.get_app_metadata.return_value = {
            "name": "BROTHER!!! - Hardcore Platformer",
            "type": "Game",
        }

        # DB lookup does NOT contain "100"
        db_lookup = {"200": ("game", "Known Game")}

        count = service.discover_missing_games(
            localconfig,
            appinfo,
            packageinfo_ids={"100", "200"},
            db_type_lookup=db_lookup,
        )

        assert count == 2
        assert "100" in games
        assert games["100"].name == "BROTHER!!! - Hardcore Platformer"
        assert games["100"].app_type == "game"
        # appinfo_manager was called for the fallback ID
        appinfo.get_app_metadata.assert_called_once_with("100")

    def test_fallback_skips_non_discoverable_types(self, tmp_path):
        """Fallback path still filters non-discoverable types like DLC."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = []

        appinfo = MagicMock()
        appinfo.appinfo = True
        appinfo.get_app_metadata.return_value = {"name": "Some DLC", "type": "dlc"}

        count = service.discover_missing_games(
            localconfig,
            appinfo,
            packageinfo_ids={"100"},
            db_type_lookup={},
        )

        assert count == 0
        assert "100" not in games

    def test_fallback_lazy_loads_appinfo(self, tmp_path):
        """Fallback triggers lazy appinfo.vdf load when not yet loaded."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = []

        appinfo = MagicMock()
        appinfo.appinfo = None  # Not yet loaded
        appinfo.get_app_metadata.return_value = {"name": "New Game", "type": "game"}

        count = service.discover_missing_games(
            localconfig,
            appinfo,
            packageinfo_ids={"100"},
            db_type_lookup={},
        )

        assert count == 1
        appinfo.load_appinfo.assert_called_once()

    def test_fallback_handles_placeholder_name(self, tmp_path):
        """Fallback uses cache or fallback name when appinfo has no real name."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = []

        appinfo = MagicMock()
        appinfo.appinfo = True
        appinfo.get_app_metadata.return_value = {"name": "", "type": "game"}

        count = service.discover_missing_games(
            localconfig,
            appinfo,
            packageinfo_ids={"100"},
            db_type_lookup={},
        )

        assert count == 1
        assert "100" in games
        # Should have a fallback name (not empty)
        assert games["100"].name != ""


class TestApplyCustomOverrides:
    """Tests for apply_custom_overrides."""

    def test_apply_custom_overrides_name(self, tmp_path):
        """Name override is applied and name_overridden flag is set."""
        game = Game(app_id="440", name="TF2")
        games = {"440": game}
        service = MetadataEnrichmentService(games, tmp_path)

        modifications = {"440": {"modified": {"name": "Team Fortress 2 Custom"}}}
        service.apply_custom_overrides(modifications)

        assert game.name == "Team Fortress 2 Custom"
        assert game.name_overridden is True

    def test_apply_custom_overrides_skips_unknown(self, tmp_path):
        """Overrides for unknown games are silently skipped."""
        games: dict[str, Game] = {"440": Game(app_id="440", name="TF2")}
        service = MetadataEnrichmentService(games, tmp_path)

        modifications = {"999": {"modified": {"name": "Ghost Game"}}}
        service.apply_custom_overrides(modifications)

        # Should not raise, and existing games unaffected
        assert games["440"].name == "TF2"
