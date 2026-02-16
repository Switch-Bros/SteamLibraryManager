# tests/unit/test_ui/test_workers.py

"""Unit tests for background workers (GameLoadWorker, SessionRestoreWorker)."""

from unittest.mock import MagicMock, patch


class TestGameLoadWorker:
    """Tests for GameLoadWorker thread."""

    def test_constructor_stores_params(self):
        """Worker should store game_service and user_id."""
        from src.ui.workers.game_load_worker import GameLoadWorker

        mock_service = MagicMock()
        worker = GameLoadWorker(mock_service, "76561198000000000")

        assert worker.game_service is mock_service
        assert worker.user_id == "76561198000000000"

    def test_run_calls_load_and_prepare(self, qtbot):
        """run() should call game_service.load_and_prepare with callback."""
        from src.ui.workers.game_load_worker import GameLoadWorker

        mock_service = MagicMock()
        mock_service.load_and_prepare.return_value = True

        worker = GameLoadWorker(mock_service, "12345")
        finished_signals = []
        worker.finished.connect(lambda ok: finished_signals.append(ok))

        # Call run() directly (not start() to avoid real threading)
        worker.run()

        mock_service.load_and_prepare.assert_called_once()
        call_args = mock_service.load_and_prepare.call_args
        assert call_args[0][0] == "12345"
        assert len(finished_signals) == 1
        assert finished_signals[0] is True

    def test_run_emits_false_on_failure(self, qtbot):
        """run() should emit finished(False) when loading fails."""
        from src.ui.workers.game_load_worker import GameLoadWorker

        mock_service = MagicMock()
        mock_service.load_and_prepare.return_value = False

        worker = GameLoadWorker(mock_service, "12345")
        finished_signals = []
        worker.finished.connect(lambda ok: finished_signals.append(ok))

        worker.run()

        assert finished_signals == [False]

    def test_run_forwards_progress(self, qtbot):
        """run() should forward progress callbacks to signal."""
        from src.ui.workers.game_load_worker import GameLoadWorker

        mock_service = MagicMock()

        def fake_load(user_id, callback):
            callback("Step 1", 1, 10)
            callback("Step 2", 5, 10)
            return True

        mock_service.load_and_prepare.side_effect = fake_load

        worker = GameLoadWorker(mock_service, "12345")
        progress = []
        worker.progress_update.connect(lambda s, c, t: progress.append((s, c, t)))

        worker.run()

        assert ("Step 1", 1, 10) in progress
        assert ("Step 2", 5, 10) in progress


class TestSessionRestoreResult:
    """Tests for the SessionRestoreResult dataclass."""

    def test_default_values(self):
        """SessionRestoreResult should have sensible defaults."""
        from src.ui.workers.session_restore_worker import SessionRestoreResult

        result = SessionRestoreResult(success=False)

        assert result.success is False
        assert result.access_token is None
        assert result.refresh_token is None
        assert result.steam_id is None
        assert result.persona_name is None

    def test_frozen_immutability(self):
        """SessionRestoreResult should be frozen (immutable)."""
        import pytest
        from src.ui.workers.session_restore_worker import SessionRestoreResult

        result = SessionRestoreResult(success=True, access_token="abc")

        with pytest.raises(AttributeError):
            result.access_token = "modified"  # type: ignore[misc]

    def test_full_construction(self):
        """SessionRestoreResult should store all fields correctly."""
        from src.ui.workers.session_restore_worker import SessionRestoreResult

        result = SessionRestoreResult(
            success=True,
            access_token="at_123",
            refresh_token="rt_456",
            steam_id="76561198000000000",
            persona_name="TestPlayer",
        )

        assert result.success is True
        assert result.access_token == "at_123"
        assert result.persona_name == "TestPlayer"


class TestSessionRestoreWorker:
    """Tests for SessionRestoreWorker thread.

    Notes on patch paths: SessionRestoreWorker imports TokenStore and
    requests locally inside methods (``from src.core.token_store import
    TokenStore`` and ``import requests``).  We therefore patch at the
    *source* module rather than the worker module.
    """

    @patch("src.core.token_store.TokenStore")
    def test_run_no_stored_tokens_emits_failure(self, mock_store_cls, qtbot):
        """No stored tokens should emit SessionRestoreResult(success=False)."""
        from src.ui.workers.session_restore_worker import SessionRestoreWorker

        mock_store = MagicMock()
        mock_store.load_tokens.return_value = None
        mock_store_cls.return_value = mock_store

        worker = SessionRestoreWorker()
        results = []
        worker.session_restored.connect(lambda r: results.append(r))

        worker.run()

        assert len(results) == 1
        assert results[0].success is False

    @patch("src.core.token_store.TokenStore")
    def test_run_refresh_success_emits_new_token(self, mock_store_cls, qtbot):
        """Successful refresh should emit result with new access_token."""
        from src.ui.workers.session_restore_worker import SessionRestoreWorker

        mock_stored = MagicMock()
        mock_stored.access_token = "old_token"
        mock_stored.refresh_token = "rt_123"
        mock_stored.steam_id = "76561198000000000"
        mock_stored.timestamp = 1700000000.0

        mock_store = MagicMock()
        mock_store.load_tokens.return_value = mock_stored
        mock_store.refresh_access_token.return_value = "fresh_token"
        mock_store_cls.return_value = mock_store

        worker = SessionRestoreWorker()
        worker.fetch_steam_persona_name = MagicMock(return_value="TestPlayer")
        results = []
        worker.session_restored.connect(lambda r: results.append(r))

        worker.run()

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].access_token == "fresh_token"
        assert results[0].persona_name == "TestPlayer"

    @patch("src.core.token_store.TokenStore")
    def test_run_refresh_and_validate_fail_emits_failure(self, mock_store_cls, qtbot):
        """Both refresh and validate failing should emit failure."""
        from src.ui.workers.session_restore_worker import SessionRestoreWorker

        mock_stored = MagicMock()
        mock_stored.access_token = "expired_token"
        mock_stored.refresh_token = "rt_123"
        mock_stored.steam_id = "76561198000000000"
        mock_stored.timestamp = 1700000000.0

        mock_store = MagicMock()
        mock_store.load_tokens.return_value = mock_stored
        mock_store.refresh_access_token.return_value = None
        mock_store_cls.return_value = mock_store
        mock_store_cls.validate_access_token = MagicMock(return_value=False)

        worker = SessionRestoreWorker()
        results = []
        worker.session_restored.connect(lambda r: results.append(r))

        worker.run()

        assert len(results) == 1
        assert results[0].success is False

    @patch("requests.get")
    def test_fetch_persona_name_success(self, mock_get):
        """Should extract persona name from Steam XML response."""
        from src.ui.workers.session_restore_worker import SessionRestoreWorker

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <profile>
            <steamID64>76561198000000000</steamID64>
            <steamID>CoolPlayer</steamID>
        </profile>"""
        mock_get.return_value = mock_response

        result = SessionRestoreWorker.fetch_steam_persona_name("76561198000000000")

        assert result == "CoolPlayer"

    @patch("requests.get")
    def test_fetch_persona_name_network_error(self, mock_get):
        """Network error should return None."""
        import requests as req

        mock_get.side_effect = req.RequestException("offline")

        from src.ui.workers.session_restore_worker import SessionRestoreWorker

        result = SessionRestoreWorker.fetch_steam_persona_name("76561198000000000")

        assert result is None
