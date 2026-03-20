# tests/unit/test_core/test_game.py

"""Tests for the Game dataclass and filtering utilities."""

from steam_library_manager.core.game import (
    Game,
    NON_GAME_APP_IDS,
    NON_GAME_NAME_PATTERNS,
    is_library_entry,
    is_real_game,
)


class TestGameDataclass:
    """Tests for the Game dataclass."""

    def test_game_defaults(self):
        """Test that Game initializes with correct defaults."""
        game = Game(app_id="440", name="Team Fortress 2")
        assert game.app_id == "440"
        assert game.name == "Team Fortress 2"
        assert game.playtime_minutes == 0
        assert game.categories == []
        assert game.genres == []
        assert game.tags == []
        assert game.sort_name == "Team Fortress 2"
        assert game.hidden is False

    def test_game_sort_name_defaults_to_name(self):
        """Test that sort_name defaults to name when not specified."""
        game = Game(app_id="1", name="Alpha Game")
        assert game.sort_name == "Alpha Game"

    def test_game_sort_name_preserved_when_set(self):
        """Test that explicit sort_name is not overwritten."""
        game = Game(app_id="1", name="The Alpha Game", sort_name="Alpha Game, The")
        assert game.sort_name == "Alpha Game, The"

    def test_playtime_hours_conversion(self):
        """Test playtime conversion from minutes to hours."""
        game = Game(app_id="1", name="Test", playtime_minutes=150)
        assert game.playtime_hours == 2.5

    def test_playtime_hours_zero(self):
        """Test playtime conversion with zero minutes."""
        game = Game(app_id="1", name="Test", playtime_minutes=0)
        assert game.playtime_hours == 0.0

    def test_has_category_true(self):
        """Test has_category returns True for existing category."""
        game = Game(app_id="1", name="Test")
        game.categories = ["Action", "RPG"]
        assert game.has_category("Action") is True

    def test_has_category_false(self):
        """Test has_category returns False for missing category."""
        game = Game(app_id="1", name="Test")
        game.categories = ["Action"]
        assert game.has_category("RPG") is False


class TestNonGameConstants:
    """Tests for NON_GAME_APP_IDS and NON_GAME_NAME_PATTERNS."""

    def test_non_game_app_ids_contains_proton(self):
        """Test that NON_GAME_APP_IDS contains major Proton versions."""
        expected_proton = {"1887720", "1493710", "1420170"}
        assert expected_proton.issubset(NON_GAME_APP_IDS)

    def test_non_game_app_ids_contains_steam_runtime(self):
        """Test that NON_GAME_APP_IDS contains Steam Linux Runtime."""
        assert "1628350" in NON_GAME_APP_IDS
        assert "1391110" in NON_GAME_APP_IDS

    def test_non_game_name_patterns_not_empty(self):
        """Test that NON_GAME_NAME_PATTERNS has entries."""
        assert len(NON_GAME_NAME_PATTERNS) > 0
        assert "Proton" in NON_GAME_NAME_PATTERNS


class TestIsRealGame:
    """Tests for the is_real_game() function."""

    def test_real_game_returns_true(self):
        """Test that a normal game is recognized as real."""
        game = Game(app_id="440", name="Team Fortress 2")
        assert is_real_game(game) is True

    def test_proton_by_id_returns_false(self):
        """Test that Proton is filtered by app ID."""
        game = Game(app_id="1493710", name="Proton Experimental")
        assert is_real_game(game) is False

    def test_proton_by_name_returns_false(self):
        """Test that Proton is filtered by name pattern."""
        game = Game(app_id="999999", name="Proton 99.0")
        assert is_real_game(game) is False

    def test_steam_runtime_by_name_returns_false(self):
        """Test that Steam Linux Runtime is filtered by name."""
        game = Game(app_id="999998", name="Steam Linux Runtime 4.0")
        assert is_real_game(game) is False

    def test_steamworks_by_id_returns_false(self):
        """Test that Steamworks Common is filtered by ID."""
        game = Game(app_id="228980", name="Steamworks Common Redistributables")
        assert is_real_game(game) is False


class TestIsLibraryEntry:
    """Tests for is_library_entry() - visible library entries."""

    def test_game_is_library_entry(self):
        assert is_library_entry(Game(app_id="440", name="TF2", app_type="game")) is True

    def test_tool_is_library_entry(self):
        assert is_library_entry(Game(app_id="1", name="SDK", app_type="tool")) is True

    def test_application_is_library_entry(self):
        assert is_library_entry(Game(app_id="2", name="RPG Maker", app_type="application")) is True

    def test_music_is_library_entry(self):
        assert is_library_entry(Game(app_id="3", name="OST", app_type="music")) is True

    def test_video_is_library_entry(self):
        assert is_library_entry(Game(app_id="4", name="Movie", app_type="video")) is True

    def test_dlc_not_library_entry(self):
        assert is_library_entry(Game(app_id="5", name="DLC Pack", app_type="dlc")) is False

    def test_demo_not_library_entry(self):
        assert is_library_entry(Game(app_id="6", name="Demo", app_type="demo")) is False

    def test_config_not_library_entry(self):
        assert is_library_entry(Game(app_id="7", name="Config", app_type="config")) is False

    def test_proton_not_library_entry(self):
        assert is_library_entry(Game(app_id="999", name="Proton 9.0")) is False

    def test_ghost_not_library_entry(self):
        assert is_library_entry(Game(app_id="999", name="App 12345")) is False
