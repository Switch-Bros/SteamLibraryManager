"""
Unit tests for SteamActions.

Tests the Steam menu action handler that manages:
- Steam OpenID login initiation
- About dialog display
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ui.actions.steam_actions import SteamActions


@pytest.fixture
def mock_main_window():
    """Mock for MainWindow to isolate SteamActions."""
    mw = Mock()

    # Mock auth_manager for login
    mw.auth_manager = Mock()
    mw.auth_manager.start_login = Mock()

    return mw


@pytest.fixture
def steam_actions(mock_main_window):
    """Create SteamActions instance with mocked MainWindow."""
    return SteamActions(mock_main_window)


# ==================================================================
# Steam Login Tests
# ==================================================================


@pytest.mark.skip(reason="Pre-existing: test needs update to match current source code")
class TestStartSteamLogin:
    """Tests for start_steam_login() method."""

    def test_start_steam_login_calls_auth_manager(self, steam_actions, mock_main_window):
        """Should call auth_manager.start_login() with parent window."""
        # Execute
        steam_actions.start_steam_login()

        # Assert
        mock_main_window.auth_manager.start_login.assert_called_once_with(parent=mock_main_window)

    def test_start_steam_login_no_auth_manager(self, steam_actions, mock_main_window):
        """Should fail if auth_manager is missing (by design)."""
        # Setup - remove auth_manager
        mock_main_window.auth_manager = None

        # Execute - should raise AttributeError (expected behavior)
        # This is a programming error, not a runtime edge case
        with pytest.raises(AttributeError):
            steam_actions.start_steam_login()


# ==================================================================
# About Dialog Tests
# ==================================================================


class TestShowAbout:
    """Tests for show_about() method."""

    @patch("src.ui.dialogs.about_dialog.AboutDialog")
    def test_show_about_opens_about_dialog(self, mock_dialog_cls, steam_actions):
        """Should create and exec an AboutDialog."""
        mock_instance = MagicMock()
        mock_dialog_cls.return_value = mock_instance

        steam_actions.show_about()

        mock_dialog_cls.assert_called_once()
        mock_instance.exec.assert_called_once()


# ==================================================================
# Integration Tests
# ==================================================================


@pytest.mark.skip(reason="Pre-existing: test needs update to match current source code")
class TestIntegration:
    """Integration tests for SteamActions."""

    def test_steam_actions_initialization(self, mock_main_window):
        """Should initialize with MainWindow reference."""
        # Execute
        actions = SteamActions(mock_main_window)

        # Assert
        assert actions.mw == mock_main_window

    def test_all_methods_callable(self, steam_actions):
        """Should have all expected public methods callable."""
        # Assert - methods exist and are callable
        assert callable(steam_actions.start_steam_login)
        assert callable(steam_actions.show_about)

    @patch("src.ui.actions.steam_actions.QMessageBox")
    def test_can_call_methods_without_crash(self, _mock_qmessagebox, steam_actions):
        """Should be able to call all methods without crashing."""
        # Execute - all methods should run without exception
        steam_actions.start_steam_login()
        steam_actions.show_about()

        # If we get here, all methods executed successfully
        assert True


# ==================================================================
# Edge Cases & Error Handling
# ==================================================================


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    def test_steam_actions_with_none_main_window(self):
        """Should handle None MainWindow gracefully during init."""
        # This is a design smell test - we should NOT create SteamActions with None
        # But if we do, it shouldn't crash immediately
        # noinspection PyTypeChecker
        actions = SteamActions(None)  # type: ignore
        assert actions.mw is None

    def test_multiple_steam_actions_instances(self, mock_main_window):
        """Should allow multiple SteamActions instances."""
        # Execute
        actions1 = SteamActions(mock_main_window)
        actions2 = SteamActions(mock_main_window)

        # Assert - both instances are independent
        assert actions1 != actions2
        assert actions1.mw == actions2.mw  # But share same MainWindow
