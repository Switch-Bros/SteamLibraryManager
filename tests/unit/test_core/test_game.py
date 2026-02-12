# tests/unit/test_core/test_game.py

"""Tests for the Game dataclass and filtering utilities."""

from src.core.game import Game, NON_GAME_APP_IDS, NON_GAME_NAME_PATTERNS, is_real_game


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
