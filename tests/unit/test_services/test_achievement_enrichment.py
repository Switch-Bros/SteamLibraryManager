# tests/unit/test_services/test_achievement_enrichment.py

"""Tests for AchievementEnrichmentThread."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.enrichment.achievement_enrichment_service import AchievementEnrichmentThread

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def thread() -> AchievementEnrichmentThread:
    """Returns a fresh AchievementEnrichmentThread."""
    return AchievementEnrichmentThread()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class TestConfiguration:
    """Tests for thread configuration."""

    def test_configure_stores_values(self, thread: AchievementEnrichmentThread) -> None:
        """configure() stores games, db_path, api_key, steam_id."""
        games = [(100, "Game A"), (200, "Game B")]
        path = Path("/tmp/test.db")
        thread.configure(games, path, "APIKEY123", "76561198012345678")

        assert thread._games == games
        assert thread._db_path == path
        assert thread._api_key == "APIKEY123"
        assert thread._steam_id == "76561198012345678"

    def test_cancel_sets_flag(self, thread: AchievementEnrichmentThread) -> None:
        """cancel() sets the internal cancelled flag."""
        assert thread._cancelled is False
        thread.cancel()
        assert thread._cancelled is True


# ---------------------------------------------------------------------------
# _enrich_game
# ---------------------------------------------------------------------------


class TestEnrichGame:
    """Tests for _enrich_game method."""

    def test_enrich_game_with_achievements(self, thread: AchievementEnrichmentThread) -> None:
        """Games with achievements get full enrichment."""
        mock_api = MagicMock()
        mock_db = MagicMock()

        mock_api.get_game_schema.return_value = {
            "achievements": [
                {"name": "ACH_1", "displayName": "First", "description": "Do it", "hidden": 0},
                {"name": "ACH_2", "displayName": "Second", "description": "Do more", "hidden": 1},
            ]
        }
        mock_api.get_player_achievements.return_value = [
            {"apiname": "ACH_1", "achieved": 1, "unlocktime": 1700000000},
            {"apiname": "ACH_2", "achieved": 0, "unlocktime": 0},
        ]
        mock_api.get_global_achievement_percentages.return_value = {
            "ACH_1": 85.5,
            "ACH_2": 5.2,
        }

        thread._steam_id = "76561198012345678"
        result = thread._enrich_game(mock_api, mock_db, 100)

        assert result is True
        mock_db.upsert_achievements.assert_called_once()
        mock_db.upsert_achievement_stats.assert_called_once_with(100, 2, 1, 50.0, False)

    def test_enrich_game_no_achievements(self, thread: AchievementEnrichmentThread) -> None:
        """Games without achievements get stats with total=0."""
        mock_api = MagicMock()
        mock_db = MagicMock()

        mock_api.get_game_schema.return_value = {"achievements": []}

        thread._steam_id = "76561198012345678"
        result = thread._enrich_game(mock_api, mock_db, 100)

        assert result is True
        mock_db.upsert_achievement_stats.assert_called_once_with(100, 0, 0, 0.0, False)
        mock_db.upsert_achievements.assert_not_called()

    def test_enrich_game_schema_none(self, thread: AchievementEnrichmentThread) -> None:
        """Schema returning None treats game as having no achievements."""
        mock_api = MagicMock()
        mock_db = MagicMock()

        mock_api.get_game_schema.return_value = None

        thread._steam_id = "76561198012345678"
        result = thread._enrich_game(mock_api, mock_db, 100)

        assert result is True
        mock_db.upsert_achievement_stats.assert_called_once_with(100, 0, 0, 0.0, False)

    def test_enrich_game_perfect_game(self, thread: AchievementEnrichmentThread) -> None:
        """All achievements unlocked results in perfect=True."""
        mock_api = MagicMock()
        mock_db = MagicMock()

        mock_api.get_game_schema.return_value = {
            "achievements": [
                {"name": "ACH_1", "displayName": "First"},
            ]
        }
        mock_api.get_player_achievements.return_value = [
            {"apiname": "ACH_1", "achieved": 1, "unlocktime": 1700000000},
        ]
        mock_api.get_global_achievement_percentages.return_value = {"ACH_1": 95.0}

        thread._steam_id = "76561198012345678"
        result = thread._enrich_game(mock_api, mock_db, 100)

        assert result is True
        mock_db.upsert_achievement_stats.assert_called_once_with(100, 1, 1, 100.0, True)

    def test_enrich_game_no_player_data(self, thread: AchievementEnrichmentThread) -> None:
        """Missing player achievements → 0 unlocked."""
        mock_api = MagicMock()
        mock_db = MagicMock()

        mock_api.get_game_schema.return_value = {
            "achievements": [
                {"name": "ACH_1", "displayName": "First"},
            ]
        }
        mock_api.get_player_achievements.return_value = None
        mock_api.get_global_achievement_percentages.return_value = {}

        thread._steam_id = "76561198012345678"
        result = thread._enrich_game(mock_api, mock_db, 100)

        assert result is True
        mock_db.upsert_achievement_stats.assert_called_once_with(100, 1, 0, 0.0, False)


# ---------------------------------------------------------------------------
# run() method
# ---------------------------------------------------------------------------


class TestRunMethod:
    """Tests for the run() method."""

    def test_run_missing_config_emits_error(self, thread: AchievementEnrichmentThread) -> None:
        """run() with missing config emits error signal."""
        error_handler = MagicMock()
        thread.error.connect(error_handler)

        thread._games = [(100, "Game")]
        thread._db_path = None  # Missing!
        thread._api_key = "KEY"
        thread._steam_id = "ID"

        thread.run()
        error_handler.assert_called_once()

    def test_run_missing_api_key_emits_error(self, thread: AchievementEnrichmentThread) -> None:
        """run() with empty API key emits error signal."""
        error_handler = MagicMock()
        thread.error.connect(error_handler)

        thread._games = [(100, "Game")]
        thread._db_path = Path("/tmp/test.db")
        thread._api_key = ""  # Missing!
        thread._steam_id = "ID"

        thread.run()
        error_handler.assert_called_once()

    @patch("src.core.database.Database")
    @patch("src.integrations.steam_web_api.SteamWebAPI")
    @patch("time.sleep")
    def test_run_cancellation_stops_early(
        self,
        _mock_sleep: MagicMock,
        mock_api_cls: MagicMock,
        mock_db_cls: MagicMock,
        thread: AchievementEnrichmentThread,
    ) -> None:
        """Cancellation stops processing after current game."""
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api

        thread.configure(
            [(100, "A"), (200, "B"), (300, "C")],
            Path("/tmp/test.db"),
            "KEY",
            "STEAMID",
        )

        # Cancel after first game
        def cancel_after_first(*_args: object, **_kwargs: object) -> bool:
            thread.cancel()
            return True

        thread._enrich_game = cancel_after_first  # type: ignore[assignment]

        finished_handler = MagicMock()
        thread.finished_enrichment.connect(finished_handler)
        thread.run()

        finished_handler.assert_called_once()
        # Should have processed only 1 game before cancellation
        success, _failed = finished_handler.call_args[0]
        assert success == 1

    @patch("src.core.database.Database")
    @patch("src.integrations.steam_web_api.SteamWebAPI")
    @patch("time.sleep")
    def test_run_counts_success_and_failures(
        self,
        _mock_sleep: MagicMock,
        mock_api_cls: MagicMock,
        mock_db_cls: MagicMock,
        thread: AchievementEnrichmentThread,
    ) -> None:
        """run() correctly counts successes and failures."""
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api

        thread.configure(
            [(100, "Good"), (200, "Bad")],
            Path("/tmp/test.db"),
            "KEY",
            "STEAMID",
        )

        call_count = [0]

        def enrich_side_effect(*_args: object, **_kwargs: object) -> bool:
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("API Error")
            return True

        thread._enrich_game = enrich_side_effect  # type: ignore[assignment]

        finished_handler = MagicMock()
        thread.finished_enrichment.connect(finished_handler)
        thread.run()

        finished_handler.assert_called_once()
        success, failed = finished_handler.call_args[0]
        assert success == 1
        assert failed == 1
