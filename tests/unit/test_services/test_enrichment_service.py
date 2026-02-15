"""Tests for the EnrichmentWorker service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.integrations.hltb_api import HLTBResult
from src.services.enrichment_service import EnrichmentWorker


@pytest.fixture
def enrichment_db(tmp_path: Path):
    """Creates a minimal in-memory database with required tables."""
    db_path = tmp_path / "enrichment_test.db"

    # Create a mock database with the tables we need
    from src.core.database import Database

    db = Database(db_path)

    # Insert test games
    db.conn.execute(
        "INSERT INTO games (app_id, name, app_type, developer, platforms, created_at, updated_at) "
        "VALUES (440, 'Team Fortress 2', 'game', '', '[]', 0, 0)"
    )
    db.conn.execute(
        "INSERT INTO games (app_id, name, app_type, developer, platforms, created_at, updated_at) "
        "VALUES (570, 'Dota 2', 'game', '', '[]', 0, 0)"
    )
    db.conn.commit()
    yield db
    db.close()


class TestHLTBEnrichment:
    """Tests for run_hltb_enrichment."""

    def test_hltb_enrichment_updates_database(self, enrichment_db) -> None:
        """Successful HLTB search inserts data into hltb_data table."""
        worker = EnrichmentWorker()

        mock_client = MagicMock()
        mock_client.search_game.return_value = HLTBResult(
            game_name="Team Fortress 2",
            main_story=0.0,
            main_extras=0.0,
            completionist=0.0,
        )
        # First game has no data (main_story=0), second has data
        mock_client.search_game.side_effect = [
            HLTBResult(game_name="TF2", main_story=50.0, main_extras=100.0, completionist=500.0),
            HLTBResult(game_name="Dota 2", main_story=200.0, main_extras=0.0, completionist=0.0),
        ]

        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        games = [(440, "Team Fortress 2"), (570, "Dota 2")]
        worker.run_hltb_enrichment(games, enrichment_db, mock_client)

        # Check database was updated
        cursor = enrichment_db.conn.execute("SELECT COUNT(*) FROM hltb_data")
        count = cursor.fetchone()[0]
        assert count == 2

        finished_spy.assert_called_once_with(2, 0)

    def test_enrichment_continues_on_single_failure(self, enrichment_db) -> None:
        """Enrichment continues processing after a single game fails."""
        worker = EnrichmentWorker()

        mock_client = MagicMock()
        mock_client.search_game.side_effect = [
            Exception("API error"),
            HLTBResult(game_name="Dota 2", main_story=200.0, main_extras=0.0, completionist=0.0),
        ]

        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        games = [(440, "Team Fortress 2"), (570, "Dota 2")]
        worker.run_hltb_enrichment(games, enrichment_db, mock_client)

        finished_spy.assert_called_once_with(1, 1)

    def test_cancel_stops_processing(self, enrichment_db) -> None:
        """Cancellation stops processing remaining games."""
        worker = EnrichmentWorker()

        mock_client = MagicMock()
        # Cancel after first search
        mock_client.search_game.side_effect = lambda name: (
            worker.cancel(),
            HLTBResult(game_name=name, main_story=10.0, main_extras=0.0, completionist=0.0),
        )[1]

        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        games = [(440, "TF2"), (570, "Dota 2"), (730, "CS2")]
        worker.run_hltb_enrichment(games, enrichment_db, mock_client)

        # Should have processed only the first game before cancel took effect
        assert mock_client.search_game.call_count == 1
        finished_spy.assert_called_once_with(1, 0)


class TestSteamAPIEnrichment:
    """Tests for run_steam_api_enrichment."""

    @patch("src.integrations.steam_web_api.requests.get")
    def test_steam_api_enrichment_batches_correctly(self, mock_get: MagicMock, enrichment_db) -> None:
        """Steam API enrichment processes games in batches."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "store_items": [
                    {
                        "id": 440,
                        "name": "Team Fortress 2",
                        "basic_info": {
                            "developers": [{"name": "Valve"}],
                            "publishers": [{"name": "Valve"}],
                            "is_free": True,
                        },
                        "platforms": {"windows": True, "linux": True},
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        worker = EnrichmentWorker()
        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        games = [(440, "Team Fortress 2")]
        worker.run_steam_api_enrichment(games, enrichment_db, "test_api_key")

        finished_spy.assert_called_once()
        success, failed = finished_spy.call_args[0]
        assert success >= 1

    def test_enrichment_skips_already_enriched(self, enrichment_db) -> None:
        """get_apps_missing_metadata returns only games missing data."""
        # Update TF2 to have developer
        enrichment_db.conn.execute("UPDATE games SET developer = 'Valve' WHERE app_id = 440")
        enrichment_db.conn.commit()

        missing = enrichment_db.get_apps_missing_metadata()
        app_ids = [aid for aid, _ in missing]

        # Only Dota 2 (570) should be missing
        assert 440 not in app_ids
        assert 570 in app_ids
