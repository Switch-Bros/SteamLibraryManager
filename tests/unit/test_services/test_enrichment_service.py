"""Tests for the EnrichmentThread service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.integrations.hltb_api import HLTBResult
from src.services.enrichment_service import EnrichmentThread


@pytest.fixture
def enrichment_db(tmp_path: Path):
    """Creates a minimal database with required tables."""
    db_path = tmp_path / "enrichment_test.db"

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
    """Tests for HLTB enrichment via EnrichmentThread."""

    def test_hltb_enrichment_updates_database(self, enrichment_db) -> None:
        """Successful HLTB search inserts data into hltb_data table."""
        thread = EnrichmentThread()

        mock_client = MagicMock()
        mock_client.search_game.side_effect = [
            HLTBResult(game_name="TF2", main_story=50.0, main_extras=100.0, completionist=500.0),
            HLTBResult(game_name="Dota 2", main_story=200.0, main_extras=0.0, completionist=0.0),
        ]

        finished_spy = MagicMock()
        thread.finished_enrichment.connect(finished_spy)

        games = [(440, "Team Fortress 2"), (570, "Dota 2")]
        thread.configure_hltb(games, enrichment_db.db_path, mock_client)
        thread.run()

        # Re-read from the same DB file to verify
        from src.core.database import Database

        verify_db = Database(enrichment_db.db_path)
        cursor = verify_db.conn.execute("SELECT COUNT(*) FROM hltb_data")
        count = cursor.fetchone()[0]
        verify_db.close()
        assert count == 2

        finished_spy.assert_called_once_with(2, 0)

    def test_enrichment_continues_on_single_failure(self, enrichment_db) -> None:
        """Enrichment continues processing after a single game fails."""
        thread = EnrichmentThread()

        mock_client = MagicMock()
        mock_client.search_game.side_effect = [
            Exception("API error"),
            HLTBResult(game_name="Dota 2", main_story=200.0, main_extras=0.0, completionist=0.0),
        ]

        finished_spy = MagicMock()
        thread.finished_enrichment.connect(finished_spy)

        games = [(440, "Team Fortress 2"), (570, "Dota 2")]
        thread.configure_hltb(games, enrichment_db.db_path, mock_client)
        thread.run()

        finished_spy.assert_called_once_with(1, 1)

    def test_cancel_stops_processing(self, enrichment_db) -> None:
        """Cancellation stops processing remaining games."""
        thread = EnrichmentThread()

        mock_client = MagicMock()
        mock_client.search_game.side_effect = lambda name, app_id=0: (
            thread.cancel(),
            HLTBResult(game_name=name, main_story=10.0, main_extras=0.0, completionist=0.0),
        )[1]

        finished_spy = MagicMock()
        thread.finished_enrichment.connect(finished_spy)

        games = [(440, "TF2"), (570, "Dota 2"), (730, "CS2")]
        thread.configure_hltb(games, enrichment_db.db_path, mock_client)
        thread.run()

        assert mock_client.search_game.call_count == 1
        finished_spy.assert_called_once_with(1, 0)


class TestSteamAPIEnrichment:
    """Tests for Steam API enrichment via EnrichmentThread."""

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

        thread = EnrichmentThread()
        finished_spy = MagicMock()
        thread.finished_enrichment.connect(finished_spy)

        games = [(440, "Team Fortress 2")]
        thread.configure_steam(games, enrichment_db.db_path, "test_api_key")
        thread.run()

        finished_spy.assert_called_once()
        success, failed = finished_spy.call_args[0]
        assert success >= 1

    def test_enrichment_skips_already_enriched(self, enrichment_db) -> None:
        """get_apps_missing_metadata returns only games missing data."""
        enrichment_db.conn.execute(
            "UPDATE games SET developer = 'Valve', publisher = 'Valve',"
            " steam_release_date = 1191970800 WHERE app_id = 440"
        )
        enrichment_db.conn.commit()

        missing = enrichment_db.get_apps_missing_metadata()
        app_ids = [aid for aid, _ in missing]

        assert 440 not in app_ids
        assert 570 in app_ids
