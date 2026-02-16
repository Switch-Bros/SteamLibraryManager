# tests/unit/test_services/test_bootstrap_service.py

"""Unit tests for BootstrapService startup orchestration."""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QObject


@pytest.fixture
def make_bootstrap_service(qtbot):
    """Factory fixture that creates a BootstrapService with a real QObject parent.

    BootstrapService.__init__ calls super().__init__(parent=main_window),
    which requires a real QObject.  We pass a plain QObject as parent,
    then override service.mw with a MagicMock for test convenience.
    """
    from src.services.bootstrap_service import BootstrapService

    def _make(mw=None):
        parent = QObject()
        service = BootstrapService(parent)
        service._test_parent = parent  # prevent GC from destroying the C++ object
        service.mw = mw if mw is not None else MagicMock()
        return service

    return _make


class TestBootstrapServiceSignals:
    """Tests for BootstrapService signal emission."""

    def test_start_emits_loading_started(self, make_bootstrap_service):
        """start() should emit loading_started immediately."""
        service = make_bootstrap_service()

        with patch.object(service, "_quick_init", return_value=False):
            signals = []
            service.loading_started.connect(lambda: signals.append("loading_started"))
            service.bootstrap_complete.connect(lambda: signals.append("bootstrap_complete"))

            service.start()

        assert "loading_started" in signals

    def test_start_emits_bootstrap_complete_on_quick_init_failure(self, make_bootstrap_service):
        """start() should emit bootstrap_complete if _quick_init fails."""
        service = make_bootstrap_service()

        with patch.object(service, "_quick_init", return_value=False):
            signals = []
            service.bootstrap_complete.connect(lambda: signals.append("complete"))

            service.start()

        assert "complete" in signals

    def test_start_launches_workers_on_quick_init_success(self, make_bootstrap_service):
        """start() should launch both workers if _quick_init succeeds."""
        service = make_bootstrap_service()

        with (
            patch.object(service, "_quick_init", return_value=True),
            patch.object(service, "_start_session_worker") as mock_session,
            patch.object(service, "_start_game_worker") as mock_game,
        ):
            service.start()

        mock_session.assert_called_once()
        mock_game.assert_called_once()


class TestBootstrapServiceCheckComplete:
    """Tests for completion logic."""

    def test_check_complete_emits_only_when_both_done(self, make_bootstrap_service):
        """bootstrap_complete should only emit when session AND games are done."""
        service = make_bootstrap_service()
        signals = []
        service.bootstrap_complete.connect(lambda: signals.append("complete"))

        # Only session done — should NOT emit
        service._session_done = True
        service._games_done = False
        service._check_complete()
        assert len(signals) == 0

        # Only games done — should NOT emit
        service._session_done = False
        service._games_done = True
        service._check_complete()
        assert len(signals) == 0

        # Both done — should emit
        service._session_done = True
        service._games_done = True
        service._check_complete()
        assert len(signals) == 1

    def test_start_resets_completion_flags(self, make_bootstrap_service):
        """start() should reset _session_done and _games_done."""
        service = make_bootstrap_service()
        service._session_done = True
        service._games_done = True

        with patch.object(service, "_quick_init", return_value=False):
            service.start()

        assert service._session_done is False
        assert service._games_done is False


class TestBootstrapServiceSessionRestore:
    """Tests for session restore signal handling."""

    def test_on_session_restored_success(self, make_bootstrap_service):
        """Successful session restore should update mw state and emit signals."""
        mw = MagicMock()
        mw.steam_username = None
        service = make_bootstrap_service(mw)

        signals = []
        service.session_restored.connect(lambda ok: signals.append(("session", ok)))
        service.persona_resolved.connect(lambda name: signals.append(("persona", name)))

        result = MagicMock()
        result.success = True
        result.access_token = "at_123"
        result.refresh_token = "rt_456"
        result.steam_id = "76561198000000000"
        result.persona_name = "TestPlayer"

        service._games_done = True  # So _check_complete doesn't block

        with (
            patch("src.services.bootstrap_service.config"),
            patch("src.services.bootstrap_service.t", side_effect=lambda k, **kw: k),
        ):
            service._on_session_restored(result)

        assert service._session_done is True
        assert mw.access_token == "at_123"
        assert mw.refresh_token == "rt_456"
        assert mw.steam_username == "TestPlayer"
        assert ("session", True) in signals
        assert ("persona", "TestPlayer") in signals

    def test_on_session_restored_failure(self, make_bootstrap_service):
        """Failed session restore should emit session_restored(False)."""
        service = make_bootstrap_service()

        signals = []
        service.session_restored.connect(lambda ok: signals.append(ok))

        result = MagicMock()
        result.success = False
        service._games_done = True

        with patch("src.services.bootstrap_service.t", side_effect=lambda k, **kw: k):
            service._on_session_restored(result)

        assert service._session_done is True
        assert False in signals


class TestBootstrapServiceGamesLoaded:
    """Tests for game loading completion handling."""

    def test_on_games_loaded_failure_shows_warning(self, make_bootstrap_service):
        """Failed game loading should show warning and set reload button visible."""
        mw = MagicMock()
        mw.game_service = MagicMock()
        mw.game_service.game_manager = None
        service = make_bootstrap_service(mw)
        service._session_done = True

        with (
            patch("src.services.bootstrap_service.t", side_effect=lambda k, **kw: k),
            patch("src.ui.widgets.ui_helper.UIHelper.show_warning"),
        ):
            service._on_games_loaded(False)

        assert service._games_done is True
        mw.reload_btn.show.assert_called()

    def test_on_load_progress_forwards_signal(self, make_bootstrap_service):
        """_on_load_progress should re-emit the load_progress signal."""
        service = make_bootstrap_service()
        signals = []
        service.load_progress.connect(lambda s, c, t: signals.append((s, c, t)))

        service._on_load_progress("Loading games", 5, 100)

        assert signals == [("Loading games", 5, 100)]
