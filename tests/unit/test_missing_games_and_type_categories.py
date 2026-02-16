# tests/unit/test_missing_games_and_type_categories.py

"""Tests for missing game discovery, app_type filtering, and type categories."""

from unittest.mock import MagicMock

from src.core.game import Game, is_real_game
from src.services.enrichment.metadata_enrichment_service import MetadataEnrichmentService


class TestIsRealGameWithAppType:
    """Tests for is_real_game() when app_type is set."""

    def test_game_type_returns_true(self):
        """Test that app_type='game' is recognized as real."""
        game = Game(app_id="440", name="TF2", app_type="game")
        assert is_real_game(game) is True

    def test_game_type_case_insensitive(self):
        """Test that app_type check is case-insensitive."""
        game = Game(app_id="440", name="TF2", app_type="Game")
        assert is_real_game(game) is True

    def test_music_type_returns_false(self):
        """Test that app_type='music' is filtered out."""
        game = Game(app_id="100", name="Some Soundtrack", app_type="music")
        assert is_real_game(game) is False

    def test_tool_type_returns_false(self):
        """Test that app_type='tool' is filtered out."""
        game = Game(app_id="101", name="SDK Tool", app_type="tool")
        assert is_real_game(game) is False

    def test_application_type_returns_false(self):
        """Test that app_type='application' is filtered out."""
        game = Game(app_id="102", name="Wallpaper Engine", app_type="application")
        assert is_real_game(game) is False

    def test_video_type_returns_false(self):
        """Test that app_type='video' is filtered out."""
        game = Game(app_id="103", name="Free to Play", app_type="video")
        assert is_real_game(game) is False

    def test_dlc_type_returns_false(self):
        """Test that app_type='dlc' is filtered out."""
        game = Game(app_id="104", name="Some DLC", app_type="dlc")
        assert is_real_game(game) is False

    def test_demo_type_returns_false(self):
        """Test that app_type='demo' is filtered out."""
        game = Game(app_id="105", name="Demo Version", app_type="demo")
        assert is_real_game(game) is False

    def test_config_type_returns_false(self):
        """Test that app_type='config' is filtered out."""
        game = Game(app_id="106", name="Config Entry", app_type="config")
        assert is_real_game(game) is False

    def test_empty_app_type_falls_through_to_heuristic(self):
        """Test that empty app_type uses the old heuristic fallback."""
        # Normal game with empty type → heuristic says True
        game = Game(app_id="440", name="Team Fortress 2", app_type="")
        assert is_real_game(game) is True

        # Proton by name with empty type → heuristic says False
        proton = Game(app_id="999999", name="Proton 99.0", app_type="")
        assert is_real_game(proton) is False

    def test_unknown_type_falls_through_to_heuristic(self):
        """Test that an unrecognized app_type falls through to heuristic."""
        game = Game(app_id="440", name="Some Game", app_type="beta")
        assert is_real_game(game) is True


class TestGetAllAppIds:
    """Tests for LocalConfigHelper.get_all_app_ids()."""

    def test_returns_all_keys(self):
        """Test that get_all_app_ids returns all keys from apps dict."""
        from src.core.localconfig_helper import LocalConfigHelper

        helper = LocalConfigHelper("/nonexistent/path")
        helper.apps = {"440": {}, "570": {}, "730": {"hidden": "1"}}
        result = helper.get_all_app_ids()
        assert set(result) == {"440", "570", "730"}

    def test_returns_empty_for_empty_apps(self):
        """Test that get_all_app_ids returns empty list when no apps."""
        from src.core.localconfig_helper import LocalConfigHelper

        helper = LocalConfigHelper("/nonexistent/path")
        helper.apps = {}
        assert helper.get_all_app_ids() == []


class TestDiscoverMissingGames:
    """Tests for MetadataEnrichmentService.discover_missing_games()."""

    def test_discovers_missing_game(self, tmp_path):
        """Test that a game in localconfig but not in API is discovered."""
        games: dict[str, Game] = {
            "440": Game(app_id="440", name="TF2"),
        }
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = ["440", "570"]

        appinfo = MagicMock()
        appinfo.get_app_metadata.return_value = {
            "name": "Dota 2",
            "type": "game",
        }

        count = service.discover_missing_games(localconfig, appinfo)

        assert count == 1
        assert "570" in games
        assert games["570"].name == "Dota 2"
        assert games["570"].app_type == "game"

    def test_discovers_music_type(self, tmp_path):
        """Test that music apps are discovered (for type categories)."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = ["100"]

        appinfo = MagicMock()
        appinfo.get_app_metadata.return_value = {
            "name": "Game OST",
            "type": "music",
        }

        count = service.discover_missing_games(localconfig, appinfo)

        assert count == 1
        assert "100" in games
        assert games["100"].app_type == "music"

    def test_skips_dlc(self, tmp_path):
        """Test that DLC apps are NOT discovered."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = ["200"]

        appinfo = MagicMock()
        appinfo.get_app_metadata.return_value = {
            "name": "Some DLC Pack",
            "type": "dlc",
        }

        count = service.discover_missing_games(localconfig, appinfo)

        assert count == 0
        assert "200" not in games

    def test_skips_demo(self, tmp_path):
        """Test that demo apps are NOT discovered."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = ["300"]

        appinfo = MagicMock()
        appinfo.get_app_metadata.return_value = {
            "name": "Some Demo",
            "type": "demo",
        }

        count = service.discover_missing_games(localconfig, appinfo)

        assert count == 0
        assert "300" not in games

    def test_skips_config(self, tmp_path):
        """Test that config entries are NOT discovered."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = ["400"]

        appinfo = MagicMock()
        appinfo.get_app_metadata.return_value = {
            "name": "Config Entry",
            "type": "config",
        }

        count = service.discover_missing_games(localconfig, appinfo)

        assert count == 0

    def test_skips_already_known_games(self, tmp_path):
        """Test that games already in the dict are not re-added."""
        games: dict[str, Game] = {
            "440": Game(app_id="440", name="TF2"),
        }
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = ["440"]

        appinfo = MagicMock()

        count = service.discover_missing_games(localconfig, appinfo)

        assert count == 0
        # appinfo.get_app_metadata should never be called for known games
        appinfo.get_app_metadata.assert_not_called()

    def test_returns_zero_for_no_candidates(self, tmp_path):
        """Test that 0 is returned when localconfig has no new IDs."""
        games: dict[str, Game] = {"440": Game(app_id="440", name="TF2")}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = ["440"]

        appinfo = MagicMock()

        assert service.discover_missing_games(localconfig, appinfo) == 0


class TestDiscoverFromPackageinfo:
    """Tests for discovery via packageinfo.vdf app IDs."""

    def test_discovers_from_packageinfo_ids(self, tmp_path):
        """Test that games from packageinfo are discovered."""
        games: dict[str, Game] = {"440": Game(app_id="440", name="TF2")}
        service = MetadataEnrichmentService(games, tmp_path)

        appinfo = MagicMock()
        appinfo.get_app_metadata.return_value = {
            "name": "Dark Deception",
            "type": "game",
        }

        # No localconfig, but packageinfo has the game
        count = service.discover_missing_games(None, appinfo, packageinfo_ids={"332950"})

        assert count == 1
        assert "332950" in games
        assert games["332950"].name == "Dark Deception"

    def test_packageinfo_combined_with_localconfig(self, tmp_path):
        """Test that both sources are combined."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        localconfig = MagicMock()
        localconfig.get_all_app_ids.return_value = ["100"]

        appinfo = MagicMock()
        appinfo.get_app_metadata.side_effect = lambda app_id: {
            "100": {"name": "Game A", "type": "game"},
            "200": {"name": "Game B", "type": "game"},
        }.get(app_id, {})

        count = service.discover_missing_games(localconfig, appinfo, packageinfo_ids={"200"})

        assert count == 2
        assert "100" in games
        assert "200" in games

    def test_packageinfo_skips_dlc(self, tmp_path):
        """Test that DLC from packageinfo is skipped."""
        games: dict[str, Game] = {}
        service = MetadataEnrichmentService(games, tmp_path)

        appinfo = MagicMock()
        appinfo.get_app_metadata.return_value = {
            "name": "Some DLC",
            "type": "dlc",
        }

        count = service.discover_missing_games(None, appinfo, packageinfo_ids={"999"})

        assert count == 0


class TestAppTypeAssignment:
    """Tests for app_type assignment in apply_metadata_overrides."""

    def test_sets_app_type_from_appinfo(self, tmp_path):
        """Test that app_type is set from appinfo metadata."""
        game = Game(app_id="440", name="TF2")
        games = {"440": game}
        service = MetadataEnrichmentService(games, tmp_path)

        appinfo_manager = MagicMock()
        appinfo_manager.load_appinfo.return_value = {}
        appinfo_manager.get_app_metadata.return_value = {
            "name": "Team Fortress 2",
            "type": "game",
        }

        service.apply_metadata_overrides(appinfo_manager)

        assert game.app_type == "game"

    def test_does_not_overwrite_existing_app_type(self, tmp_path):
        """Test that existing app_type is not overwritten."""
        game = Game(app_id="440", name="TF2", app_type="game")
        games = {"440": game}
        service = MetadataEnrichmentService(games, tmp_path)

        appinfo_manager = MagicMock()
        appinfo_manager.load_appinfo.return_value = {}
        appinfo_manager.get_app_metadata.return_value = {
            "type": "tool",  # Different type, should NOT overwrite
        }

        service.apply_metadata_overrides(appinfo_manager)

        assert game.app_type == "game"  # Unchanged


class TestTypeCategoriesGrouping:
    """Tests for _get_type_categories in CategoryPopulator."""

    def test_groups_by_type(self):
        """Test that apps are grouped into correct type categories."""
        from src.ui.handlers.category_populator import CategoryPopulator

        apps = [
            Game(app_id="1", name="Cool Game", app_type="game"),
            Game(app_id="2", name="Game OST", app_type="music"),
            Game(app_id="3", name="SDK", app_type="tool"),
            Game(app_id="4", name="Wallpaper Engine", app_type="application"),
            Game(app_id="5", name="Documentary", app_type="video"),
        ]

        result = CategoryPopulator._get_type_categories(apps)

        # Should have 4 categories (music, tool, application, video — NOT game)
        assert len(result) == 4

        # Verify each type is mapped correctly
        from src.utils.i18n import t

        assert t("categories.soundtracks") in result
        assert t("categories.tools") in result
        assert t("categories.software") in result
        assert t("categories.videos") in result

    def test_excludes_hidden_apps(self):
        """Test that hidden apps are excluded from type categories."""
        from src.ui.handlers.category_populator import CategoryPopulator

        apps = [
            Game(app_id="1", name="Game OST", app_type="music"),
            Game(app_id="2", name="Hidden OST", app_type="music", hidden=True),
        ]

        result = CategoryPopulator._get_type_categories(apps)
        from src.utils.i18n import t

        soundtracks = result.get(t("categories.soundtracks"), [])
        assert len(soundtracks) == 1
        assert soundtracks[0].app_id == "1"

    def test_empty_for_games_only(self):
        """Test that no type categories are created for game-only lists."""
        from src.ui.handlers.category_populator import CategoryPopulator

        apps = [
            Game(app_id="1", name="Game A", app_type="game"),
            Game(app_id="2", name="Game B", app_type="game"),
        ]

        result = CategoryPopulator._get_type_categories(apps)
        assert len(result) == 0

    def test_empty_for_unknown_type(self):
        """Test that apps with empty app_type don't create categories."""
        from src.ui.handlers.category_populator import CategoryPopulator

        apps = [
            Game(app_id="1", name="Unknown App", app_type=""),
        ]

        result = CategoryPopulator._get_type_categories(apps)
        assert len(result) == 0


class TestUncategorizedOnlyGames:
    """Tests that get_uncategorized_games() only includes actual games.

    Non-game types (music, tool, application, video) have their own type
    categories and are never shown in OHNE KATEGORIE.
    """

    def test_game_without_collection_is_uncategorized(self, tmp_path):
        """Test that a game without user collections IS uncategorized."""
        from unittest.mock import patch

        from src.core.game_manager import GameManager

        with patch("src.core.game_manager.MetadataEnrichmentService"), patch("src.core.game_manager.GameDetailService"):
            manager = GameManager(
                steam_api_key=None,
                cache_dir=tmp_path,
                steam_path=tmp_path,
            )

        manager.games["440"] = Game(app_id="440", name="TF2", app_type="game")

        uncategorized = manager.get_uncategorized_games()
        assert len(uncategorized) == 1
        assert uncategorized[0].app_id == "440"

    def test_non_game_types_excluded(self, tmp_path):
        """Test that music/tool/application/video are NOT uncategorized."""
        from unittest.mock import patch

        from src.core.game_manager import GameManager

        with patch("src.core.game_manager.MetadataEnrichmentService"), patch("src.core.game_manager.GameDetailService"):
            manager = GameManager(
                steam_api_key=None,
                cache_dir=tmp_path,
                steam_path=tmp_path,
            )

        manager.games["1"] = Game(app_id="1", name="OST", app_type="music")
        manager.games["2"] = Game(app_id="2", name="SDK", app_type="tool")
        manager.games["3"] = Game(app_id="3", name="App", app_type="application")
        manager.games["4"] = Game(app_id="4", name="Movie", app_type="video")

        uncategorized = manager.get_uncategorized_games()
        assert len(uncategorized) == 0

    def test_dlc_is_not_uncategorized(self, tmp_path):
        """Test that DLC is excluded from uncategorized."""
        from unittest.mock import patch

        from src.core.game_manager import GameManager

        with patch("src.core.game_manager.MetadataEnrichmentService"), patch("src.core.game_manager.GameDetailService"):
            manager = GameManager(
                steam_api_key=None,
                cache_dir=tmp_path,
                steam_path=tmp_path,
            )

        manager.games["100"] = Game(app_id="100", name="Some DLC", app_type="dlc")

        uncategorized = manager.get_uncategorized_games()
        assert len(uncategorized) == 0

    def test_game_with_user_collection_not_uncategorized(self, tmp_path):
        """Test that a game WITH a user collection is NOT uncategorized."""
        from unittest.mock import patch

        from src.core.game_manager import GameManager

        with patch("src.core.game_manager.MetadataEnrichmentService"), patch("src.core.game_manager.GameDetailService"):
            manager = GameManager(
                steam_api_key=None,
                cache_dir=tmp_path,
                steam_path=tmp_path,
            )

        game = Game(app_id="440", name="TF2", app_type="game")
        game.categories = ["FPS Games"]
        manager.games["440"] = game

        uncategorized = manager.get_uncategorized_games()
        assert len(uncategorized) == 0


class TestVirtualCategoriesNotSaved:
    """Tests that type categories are in the virtual set and won't be saved to cloud."""

    def test_type_categories_are_virtual(self, mock_cloud_storage_file):
        """Test that all 4 type category names are in _get_virtual_categories."""
        from src.core.cloud_storage_parser import CloudStorageParser
        from src.utils.i18n import t

        virtual = CloudStorageParser._get_virtual_categories()

        assert t("categories.soundtracks") in virtual
        assert t("categories.tools") in virtual
        assert t("categories.software") in virtual
        assert t("categories.videos") in virtual

    def test_uncategorized_still_virtual(self, mock_cloud_storage_file):
        """Test that the original virtual categories are still present."""
        from src.core.cloud_storage_parser import CloudStorageParser
        from src.utils.i18n import t

        virtual = CloudStorageParser._get_virtual_categories()

        assert t("categories.uncategorized") in virtual
        assert t("categories.all_games") in virtual
