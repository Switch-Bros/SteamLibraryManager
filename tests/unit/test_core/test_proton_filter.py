# tests/unit/test_core/test_proton_filter.py

"""Tests for Proton/Steam Tools filtering."""
import pytest
from src.core.non_game_apps import is_real_game, NON_GAME_APP_IDS


class TestProtonFilter:
    """Tests for filtering out non-game apps."""
    
    def test_is_real_game_with_real_game(self):
        """Test that real games are recognized."""
        # Team Fortress 2
        assert is_real_game('440') == True
        
        # Counter-Strike 2
        assert is_real_game('730') == True
        
        # Random game ID
        assert is_real_game('999999') == True
    
    def test_is_real_game_with_proton(self):
        """Test that Proton versions are filtered out."""
        # Proton 7.0
        assert is_real_game('1887720') == False
        
        # Proton Experimental
        assert is_real_game('1493710') == False
        
        # Proton 5.0
        assert is_real_game('1420170') == False
    
    def test_is_real_game_with_steam_runtime(self):
        """Test that Steam Linux Runtime is filtered out."""
        # Steam Linux Runtime - Soldier
        assert is_real_game('1070560') == False
        
        # Steam Linux Runtime - Sniper
        assert is_real_game('1391110') == False
    
    def test_is_real_game_with_tools(self):
        """Test that development tools are filtered out."""
        # Steamworks Common Redistributables
        assert is_real_game('1517290') == False
        
        # Source Filmmaker
        assert is_real_game('243750') == False
    
    def test_non_game_app_ids_is_set(self):
        """Test that NON_GAME_APP_IDS is a set (for fast lookup)."""
        assert isinstance(NON_GAME_APP_IDS, set)
        assert len(NON_GAME_APP_IDS) > 0
    
    def test_non_game_app_ids_contains_proton(self):
        """Test that the list contains major Proton versions."""
        # At least these Proton versions should be there
        expected_proton = {'1887720', '1493710', '1420170'}
        assert expected_proton.issubset(NON_GAME_APP_IDS)


class TestGameManagerRealGames:
    """Tests for GameManager.get_real_games() method."""
    
    def test_get_real_games_filters_proton(self, mock_config):
        """Test that get_real_games() filters out Proton."""
        from src.core.game_manager import GameManager, Game
        from pathlib import Path
        
        manager = GameManager(
            steam_api_key=None,
            cache_dir=Path("/tmp"),
            steam_path=Path("/tmp")
        )
        
        # Add real games
        manager.games['440'] = Game(app_id='440', name='Team Fortress 2')
        manager.games['730'] = Game(app_id='730', name='Counter-Strike 2')
        
        # Add Proton (should be filtered)
        manager.games['1887720'] = Game(app_id='1887720', name='Proton 7.0')
        manager.games['1493710'] = Game(app_id='1493710', name='Proton Experimental')
        
        # Get real games
        real_games = manager.get_real_games()
        
        # Should only have 2 real games
        assert len(real_games) == 2
        
        # Check that Proton is NOT in the list
        app_ids = [g.app_id for g in real_games]
        assert '440' in app_ids
        assert '730' in app_ids
        assert '1887720' not in app_ids
        assert '1493710' not in app_ids
