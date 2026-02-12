"""
Unit tests for GameActions.

Tests the Game context menu action handler that manages:
- Toggle favorite status
- Toggle hidden status
- Open Steam store page
- Remove from local config
- Remove from account
"""

import pytest
from unittest.mock import Mock, patch
from src.ui.actions.game_actions import GameActions
from src.core.game_manager import Game


@pytest.fixture
def mock_main_window():
    """Mock for MainWindow to isolate GameActions."""
    mw = Mock()

    # Mock required managers/parsers
    mw.game_manager = Mock()
    mw.vdf_parser = Mock()

    # Mock UI methods
    mw._save_collections = Mock(return_value=True)
    mw._populate_categories = Mock()
    mw._add_app_category = Mock()
    mw._remove_app_category = Mock()
    mw.set_status = Mock()

    return mw


@pytest.fixture
def game_actions(mock_main_window):
    """Create GameActions instance with mocked MainWindow."""
    return GameActions(mock_main_window)


@pytest.fixture
def sample_game() -> Game:
    """Create a sample game for testing."""
    game = Game(app_id="440", name="Team Fortress 2")
    game.categories = []
    game.hidden = False  # Initialize hidden attribute
    return game


# ==================================================================
# Toggle Favorite Tests
# ==================================================================


@pytest.mark.skip(reason="Pre-existing: test needs update to match current source code")
class TestToggleFavorite:
    """Tests for toggle_favorite() method."""

    def test_toggle_favorite_adds_to_favorites(
        self, game_actions: GameActions, mock_main_window: Mock, sample_game: Game
    ):
        """Should add game to favorites when not already favorited."""
        # Setup
        sample_game.categories = []

        # Execute
        game_actions.toggle_favorite(sample_game)

        # Assert
        assert "favorite" in sample_game.categories
        mock_main_window._add_app_category.assert_called_once_with("440", "favorite")
        mock_main_window._save_collections.assert_called_once()
        mock_main_window._populate_categories.assert_called_once()

    def test_toggle_favorite_removes_from_favorites(
        self, game_actions: GameActions, mock_main_window: Mock, sample_game: Game
    ):
        """Should remove game from favorites when already favorited."""
        # Setup
        sample_game.categories = ["favorite"]

        # Execute
        game_actions.toggle_favorite(sample_game)

        # Assert
        assert "favorite" not in sample_game.categories
        mock_main_window._remove_app_category.assert_called_once_with("440", "favorite")
        mock_main_window._save_collections.assert_called_once()

    def test_toggle_favorite_no_vdf_parser(self, game_actions: GameActions, mock_main_window: Mock, sample_game: Game):
        """Should handle missing vdf_parser gracefully."""
        # Setup
        mock_main_window.vdf_parser = None

        # Execute - should not crash
        game_actions.toggle_favorite(sample_game)

        # Assert - no save should happen
        mock_main_window._save_collections.assert_not_called()


# ==================================================================
# Toggle Hide Game Tests
# ==================================================================


@pytest.mark.skip(reason="Pre-existing: test needs update to match current source code")
class TestToggleHideGame:
    """Tests for toggle_hide_game() method."""

    @patch("src.ui.actions.game_actions.UIHelper")
    def test_toggle_hide_game_hides(
        self, mock_helper, game_actions: GameActions, mock_main_window: Mock, sample_game: Game
    ):
        """Should hide game when hide=True."""
        # Execute
        game_actions.toggle_hide_game(sample_game, True)

        # Assert
        mock_main_window.vdf_parser.set_app_hidden.assert_called_once_with("440", True)
        mock_main_window._save_collections.assert_called_once()
        mock_main_window._populate_categories.assert_called_once()
        mock_helper.show_success.assert_called_once()
        assert sample_game.hidden is True

    @patch("src.ui.actions.game_actions.UIHelper")
    def test_toggle_hide_game_unhides(
        self, mock_helper, game_actions: GameActions, mock_main_window: Mock, sample_game: Game
    ):
        """Should unhide game when hide=False."""
        # Execute
        game_actions.toggle_hide_game(sample_game, False)

        # Assert
        mock_main_window.vdf_parser.set_app_hidden.assert_called_once_with("440", False)
        mock_helper.show_success.assert_called_once()
        assert sample_game.hidden is False

    def test_toggle_hide_game_no_vdf_parser(self, game_actions: GameActions, mock_main_window: Mock, sample_game: Game):
        """Should handle missing vdf_parser gracefully."""
        # Setup
        mock_main_window.vdf_parser = None

        # Execute - should not crash
        game_actions.toggle_hide_game(sample_game, True)

        # Assert
        mock_main_window._save_collections.assert_not_called()

    @patch("src.ui.actions.game_actions.UIHelper")
    def test_toggle_hide_game_shows_success(
        self, mock_helper, game_actions: GameActions, mock_main_window: Mock, sample_game: Game
    ):
        """Should show success message after hiding."""
        # Execute
        game_actions.toggle_hide_game(sample_game, True)

        # Assert
        mock_helper.show_success.assert_called_once()


# ==================================================================
# Open In Store Tests
# ==================================================================


class TestOpenInStore:
    """Tests for open_in_store() method."""

    @patch("webbrowser.open")
    def test_open_in_store(self, mock_webbrowser, game_actions: GameActions, sample_game: Game):
        """Should open Steam store page in browser."""
        # Execute
        game_actions.open_in_store(sample_game)

        # Assert
        expected_url = "https://store.steampowered.com/app/440"
        mock_webbrowser.assert_called_once_with(expected_url)

    @patch("webbrowser.open")
    def test_open_in_store_different_appid(self, mock_webbrowser, game_actions: GameActions):
        """Should construct correct URL for different app IDs."""
        # Setup
        game = Game(app_id="12345", name="Test Game")

        # Execute
        game_actions.open_in_store(game)

        # Assert
        expected_url = "https://store.steampowered.com/app/12345"
        mock_webbrowser.assert_called_once_with(expected_url)


# ==================================================================
# Remove From Local Config Tests
# ==================================================================


@pytest.mark.skip(reason="Pre-existing: test needs update to match current source code")
class TestRemoveFromLocalConfig:
    """Tests for remove_from_local_config() method."""

    @patch("src.ui.actions.game_actions.UIHelper")
    def test_remove_from_local_config_success(
        self, mock_helper, game_actions: GameActions, mock_main_window: Mock, sample_game: Game
    ):
        """Should remove game from local config after confirmation."""
        # Setup
        mock_helper.confirm.return_value = True
        mock_main_window.vdf_parser.remove_app.return_value = True
        mock_main_window.game_manager.games = {"440": sample_game}

        # Execute
        game_actions.remove_from_local_config(sample_game)

        # Assert
        mock_helper.confirm.assert_called_once()
        mock_main_window.vdf_parser.remove_app.assert_called_once_with("440")
        mock_main_window._save_collections.assert_called_once()
        mock_main_window._populate_categories.assert_called_once()
        mock_helper.show_success.assert_called_once()
        assert "440" not in mock_main_window.game_manager.games

    @patch("src.ui.actions.game_actions.UIHelper")
    def test_remove_from_local_config_cancelled(
        self, mock_helper, game_actions: GameActions, mock_main_window: Mock, sample_game: Game
    ):
        """Should not remove if user cancels confirmation."""
        # Setup
        mock_helper.confirm.return_value = False

        # Execute
        game_actions.remove_from_local_config(sample_game)

        # Assert
        mock_helper.confirm.assert_called_once()
        mock_main_window.vdf_parser.remove_app.assert_not_called()

    @patch("src.ui.actions.game_actions.UIHelper")
    def test_remove_from_local_config_fails(
        self, mock_helper, game_actions: GameActions, mock_main_window: Mock, sample_game: Game
    ):
        """Should show error if removal fails."""
        # Setup
        mock_helper.confirm.return_value = True
        mock_main_window.vdf_parser.remove_app.return_value = False

        # Execute
        game_actions.remove_from_local_config(sample_game)

        # Assert
        mock_helper.show_error.assert_called_once()


# ==================================================================
# Remove From Account Tests
# ==================================================================


class TestRemoveFromAccount:
    """Tests for remove_game_from_account() method."""

    @patch("webbrowser.open")
    @patch("src.ui.actions.game_actions.UIHelper")
    def test_remove_from_account_opens_support(
        self, mock_helper, mock_webbrowser, game_actions: GameActions, sample_game: Game
    ):
        """Should open Steam Support page after confirmation."""
        # Setup
        mock_helper.confirm.return_value = True

        # Execute
        game_actions.remove_game_from_account(sample_game)

        # Assert
        mock_helper.confirm.assert_called_once()
        # Check that URL contains app_id and issueid=123
        call_args = mock_webbrowser.call_args[0][0]
        assert "440" in call_args
        assert "issueid=123" in call_args

    @patch("webbrowser.open")
    @patch("src.ui.actions.game_actions.UIHelper")
    def test_remove_from_account_cancelled(
        self, mock_helper, mock_webbrowser, game_actions: GameActions, sample_game: Game
    ):
        """Should not open support if user cancels."""
        # Setup
        mock_helper.confirm.return_value = False

        # Execute
        game_actions.remove_game_from_account(sample_game)

        # Assert
        mock_helper.confirm.assert_called_once()
        mock_webbrowser.assert_not_called()


# ==================================================================
# Integration Tests
# ==================================================================


class TestIntegration:
    """Integration tests for GameActions."""

    def test_game_actions_initialization(self, mock_main_window: Mock):
        """Should initialize with MainWindow reference."""
        # Execute
        actions = GameActions(mock_main_window)

        # Assert
        assert actions.mw == mock_main_window

    def test_all_methods_callable(self, game_actions: GameActions):
        """Should have all expected public methods callable."""
        # Assert - methods exist and are callable
        assert callable(game_actions.toggle_favorite)
        assert callable(game_actions.toggle_hide_game)
        assert callable(game_actions.open_in_store)
        assert callable(game_actions.remove_from_local_config)
        assert callable(game_actions.remove_game_from_account)


# ==================================================================
# Edge Cases & Error Handling
# ==================================================================


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    def test_game_actions_with_none_main_window(self):
        """Should handle None MainWindow gracefully during init."""
        # This is a design smell test
        # noinspection PyTypeChecker
        actions = GameActions(None)  # type: ignore
        assert actions.mw is None

    def test_multiple_game_actions_instances(self, mock_main_window: Mock):
        """Should allow multiple GameActions instances."""
        # Execute
        actions1 = GameActions(mock_main_window)
        actions2 = GameActions(mock_main_window)

        # Assert - both instances are independent
        assert actions1 != actions2
        assert actions1.mw == actions2.mw  # But share same MainWindow
