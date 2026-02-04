import pytest
from unittest.mock import Mock
from src.ui.actions.view_actions import ViewActions

@pytest.fixture
def mock_main_window():
    window = Mock()
    window.tree = Mock()
    window.game_manager = Mock()
    window.search_service = Mock()  # <--- Mocked Service
    window.search_entry = Mock()
    window.current_search_query = ""
    return window

def test_search_delegates_to_service(mock_main_window):
    # Setup
    game = Mock()
    game.name = "Test Game"
    
    mock_main_window.game_manager.get_real_games.return_value = [game]
    mock_main_window.search_service.filter_games.return_value = [game] # Service gibt Spiel zurück
    
    actions = ViewActions(mock_main_window)
    actions.on_search("Test")
    
    # Check correct delegation
    mock_main_window.search_service.filter_games.assert_called_once()
    mock_main_window.tree.populate_categories.assert_called_once()
