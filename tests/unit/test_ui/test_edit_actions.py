"""
Unit tests for EditActions.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.ui.actions.edit_actions import EditActions
from src.core.game_manager import Game


@pytest.fixture
def mock_mainwindow():
    """Mock for MainWindow to isolate EditActions."""
    mw = MagicMock()
    # Mock selected games list
    mw.selected_games = []
    # Mock managers/services
    mw.game_manager = MagicMock()
    mw.metadata_service = MagicMock()
    mw.appinfo_manager = MagicMock()
    mw.autocategorize_service = MagicMock()
    mw.steam_scraper = MagicMock()

    # Mock public methods required by EditActions
    mw.populate_categories = MagicMock()
    mw.on_game_selected = MagicMock()
    mw.save_collections = MagicMock()
    # Mock the parser getter
    mw._get_active_parser = MagicMock(return_value=MagicMock())

    return mw


@pytest.fixture
def edit_actions(mock_mainwindow):
    return EditActions(mock_mainwindow)


@patch("src.ui.actions.edit_actions.UIHelper")  # <--- WICHTIG: UIHelper patchen!
def test_edit_game_metadata_opens_dialog(mock_ui_helper, edit_actions, mock_mainwindow):
    """Test that edit_game_metadata prepares data and opens dialog."""
    # Setup
    game = Game("123", "Test Game")
    mock_mainwindow.metadata_service.get_game_metadata.return_value = {"name": "Test Game"}
    mock_mainwindow.metadata_service.get_original_metadata.return_value = {}

    # Mock the Dialog class specifically inside the module
    with patch("src.ui.actions.edit_actions.MetadataEditDialog") as MockDialog:
        instance = MockDialog.return_value
        instance.exec.return_value = True  # Simulate user clicking OK
        instance.get_metadata.return_value = {"name": "New Name", "developer": "Dev"}

        # Execute
        edit_actions.edit_game_metadata(game)

        # Assert
        # 1. Dialog was created
        MockDialog.assert_called_once()
        # 2. Service was called to save
        mock_mainwindow.metadata_service.set_game_metadata.assert_called_with(
            "123", {"name": "New Name", "developer": "Dev"}
        )
        # 3. UI was refreshed
        mock_mainwindow.populate_categories.assert_called_once()
        # 4. Success message was shown (on the mock, not real Qt)
        mock_ui_helper.show_success.assert_called()


@patch("src.ui.actions.edit_actions.UIHelper")  # <--- WICHTIG: UIHelper patchen!
def test_pegi_override_saves(mock_ui_helper, edit_actions, mock_mainwindow):
    """Test that PEGI override triggers appinfo manager."""
    # Execute
    edit_actions.on_pegi_override_requested("123", "18")

    # Assert
    mock_mainwindow.appinfo_manager.set_app_metadata.assert_called_with("123", {"pegi_rating": "18"})
    mock_mainwindow.appinfo_manager.save_appinfo.assert_called_once()
    # Check that success message was requested
    mock_ui_helper.show_success.assert_called()


def test_auto_categorize_checks_selection(edit_actions, mock_mainwindow):
    """Test that auto_categorize uses selected games if available."""
    # Setup selection
    game1 = Game("1", "G1")
    mock_mainwindow.selected_games = [game1]

    # We mock the internal helper to see if it gets called with our selection
    with patch.object(edit_actions, "_show_auto_categorize_dialog") as mock_show:
        edit_actions.auto_categorize()
        mock_show.assert_called_with([game1], None)
