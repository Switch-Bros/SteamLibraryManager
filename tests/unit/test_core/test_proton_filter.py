# tests/unit/test_core/test_proton_filter.py

"""Tests for Proton/Steam Tools filtering in App."""


class TestGameManagerProtonFilter:
    """Tests for filtering out non-game apps in GameManager."""

    def test_non_game_app_ids_contains_proton(self):
        """Test that NON_GAME_APP_IDS contains major Proton versions."""
        from src.core.game_manager import GameManager

        # At least these Proton versions should be there
        expected_proton = {"1887720", "1493710", "1420170"}
        assert expected_proton.issubset(GameManager.NON_GAME_APP_IDS)

    def test_is_real_game_with_real_game(self):
        """Test that real games are recognized."""
        from src.core.game import Game, is_real_game

        # Team Fortress 2
        tf2 = Game(app_id="440", name="Team Fortress 2")
        assert is_real_game(tf2) is True

        # Counter-Strike 2
        cs2 = Game(app_id="730", name="Counter-Strike: Global Offensive")
        assert is_real_game(cs2) is True

    def test_is_real_game_with_proton_id(self):
        """Test that Proton versions are filtered by ID."""
        from src.core.game import Game, is_real_game

        # Proton Experimental
        proton = Game(app_id="1493710", name="Proton Experimental")
        assert is_real_game(proton) is False

    def test_is_real_game_with_proton_name(self):
        """Test that Proton versions are filtered by name pattern."""
        from src.core.game import Game, is_real_game

        # Game with "Proton" in name (even if ID is unknown)
        proton = Game(app_id="999999", name="Proton 99.0")
        assert is_real_game(proton) is False

    def test_get_real_games_filters_proton(self, mock_config):
        """Test that get_real_games() filters out Proton on Linux."""
        from src.core.game_manager import GameManager, Game
        from pathlib import Path
        import platform

        manager = GameManager(steam_api_key=None, cache_dir=Path("/tmp"), steam_path=Path("/tmp"))

        # Add real games
        manager.games["440"] = Game(app_id="440", name="Team Fortress 2")
        manager.games["730"] = Game(app_id="730", name="Counter-Strike 2")

        # Add Proton (should be filtered on Linux)
        manager.games["1887720"] = Game(app_id="1887720", name="Proton 6.3")
        manager.games["1493710"] = Game(app_id="1493710", name="Proton Experimental")

        # Get real games
        real_games = manager.get_real_games()

        # On Linux: only 2 real games
        # On Windows: all 4 games (no filtering)
        if platform.system() == "Linux":
            assert len(real_games) == 2
            app_ids = [g.app_id for g in real_games]
            assert "440" in app_ids
            assert "730" in app_ids
            assert "1887720" not in app_ids
            assert "1493710" not in app_ids
        else:
            assert len(real_games) == 4  # Windows shows all
