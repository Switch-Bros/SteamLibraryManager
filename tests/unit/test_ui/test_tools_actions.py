import pytest
from unittest.mock import Mock, patch
from src.ui.actions.tools_actions import ToolsActions


@pytest.fixture
def mock_main_window():
    window = Mock()
    window.metadata_service = Mock()
    return window


def test_find_missing_metadata_no_service(mock_main_window):
    """Should return early if metadata service is missing."""
    mock_main_window.metadata_service = None
    actions = ToolsActions(mock_main_window)

    actions.find_missing_metadata()
    # No assertions needed, just ensuring no crash


def test_find_missing_metadata_none_found(mock_main_window):
    """Should show success message if all metadata is complete."""
    actions = ToolsActions(mock_main_window)
    mock_main_window.metadata_service.find_missing_metadata.return_value = []

    with patch("src.ui.actions.tools_actions.UIHelper") as mock_helper:
        actions.find_missing_metadata()
        mock_helper.show_success.assert_called_once()


def test_find_missing_metadata_found(mock_main_window):
    """Should open dialog if missing metadata is found."""
    actions = ToolsActions(mock_main_window)
    mock_main_window.metadata_service.find_missing_metadata.return_value = ["Game 1"]

    with patch("src.ui.actions.tools_actions.MissingMetadataDialog") as mock_dialog_cls:
        mock_dialog = Mock()
        mock_dialog_cls.return_value = mock_dialog

        actions.find_missing_metadata()

        mock_dialog_cls.assert_called_once()
        mock_dialog.exec.assert_called_once()


def test_check_store_availability_starts_thread(mock_main_window):
    """Should start the check thread and show progress."""
    actions = ToolsActions(mock_main_window)
    game = Mock()
    game.app_id = "12345"
    game.name = "Test Game"

    # Mock UIHelper.create_progress_dialog and StoreCheckThread
    with (
        patch("src.ui.actions.tools_actions.UIHelper") as mock_helper,
        patch("src.ui.actions.tools_actions.StoreCheckThread") as mock_thread_cls,
    ):
        mock_progress = Mock()
        mock_helper.create_progress_dialog.return_value = mock_progress
        mock_thread = Mock()
        mock_thread_cls.return_value = mock_thread

        actions.check_store_availability(game)

        mock_progress.show.assert_called_once()
        mock_thread.start.assert_called_once()
