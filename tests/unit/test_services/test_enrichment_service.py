"""Tests for the EnrichmentThread service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from steam_library_manager.integrations.hltb_api import HLTBResult
from steam_library_manager.services.enrichment.enrichment_service import EnrichmentThread


@pytest.fixture
def enrichment_db(tmp_path: Path):
    """Creates a minimal database with required tables."""
    db_path = tmp_path / "enrichment_test.db"

    from steam_library_manager.core.database import Database

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
        from steam_library_manager.core.database import Database

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

        def _cancel_and_return(name: str, app_id: int = 0) -> HLTBResult:
            thread.cancel()
            return HLTBResult(game_name=name, main_story=10.0, main_extras=0.0, completionist=0.0)

        mock_client.search_game.side_effect = _cancel_and_return

        finished_spy = MagicMock()
        thread.finished_enrichment.connect(finished_spy)

        games = [(440, "TF2"), (570, "Dota 2"), (730, "CS2")]
        thread.configure_hltb(games, enrichment_db.db_path, mock_client)
        thread.run()

        assert mock_client.search_game.call_count == 1
        finished_spy.assert_called_once_with(1, 0)


class TestPEGIBatchExtraction:
    """Tests for PEGI extraction from batch Steam API responses."""

    @patch("steam_library_manager.integrations.steam_web_api.requests.get")
    def test_pegi_extracted_from_batch_ratings_pegi_direct(self, mock_get: MagicMock, enrichment_db) -> None:
        """Direct PEGI rating is used when present in batch response."""
        from steam_library_manager.integrations.steam_web_api import SteamAppDetails

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"store_items": []}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        thread = EnrichmentThread()
        finished_spy = MagicMock()
        thread.finished_enrichment.connect(finished_spy)

        with patch("steam_library_manager.integrations.steam_web_api.SteamWebAPI.get_app_details_batch") as mock_batch:
            mock_batch.return_value = {
                440: SteamAppDetails(app_id=440, name="TF2", age_ratings=(("PEGI", "12"),)),
            }
            thread.configure_steam([(440, "TF2")], enrichment_db.db_path, "test_key")
            thread.run()

        from steam_library_manager.core.database import Database

        db = Database(enrichment_db.db_path)
        row = db.conn.execute("SELECT pegi_rating FROM games WHERE app_id = 440").fetchone()
        db.close()
        assert row[0] == "12"

    @patch("steam_library_manager.integrations.steam_web_api.requests.get")
    def test_pegi_extracted_from_batch_ratings_esrb_mapping(self, mock_get: MagicMock, enrichment_db) -> None:
        """ESRB maps to PEGI via convert_to_pegi() when no PEGI present."""
        from steam_library_manager.integrations.steam_web_api import SteamAppDetails

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"store_items": []}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        thread = EnrichmentThread()
        finished_spy = MagicMock()
        thread.finished_enrichment.connect(finished_spy)

        with patch("steam_library_manager.integrations.steam_web_api.SteamWebAPI.get_app_details_batch") as mock_batch:
            mock_batch.return_value = {
                440: SteamAppDetails(app_id=440, name="TF2", age_ratings=(("ESRB", "T"),)),
            }
            thread.configure_steam([(440, "TF2")], enrichment_db.db_path, "test_key")
            thread.run()

        from steam_library_manager.core.database import Database

        db = Database(enrichment_db.db_path)
        row = db.conn.execute("SELECT pegi_rating FROM games WHERE app_id = 440").fetchone()
        db.close()
        assert row[0] == "12"

    @patch("steam_library_manager.integrations.steam_web_api.requests.get")
    def test_pegi_prefers_pegi_over_esrb(self, mock_get: MagicMock, enrichment_db) -> None:
        """PEGI takes priority when both PEGI and ESRB are in age_ratings."""
        from steam_library_manager.integrations.steam_web_api import SteamAppDetails

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"store_items": []}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        thread = EnrichmentThread()
        finished_spy = MagicMock()
        thread.finished_enrichment.connect(finished_spy)

        with patch("steam_library_manager.integrations.steam_web_api.SteamWebAPI.get_app_details_batch") as mock_batch:
            mock_batch.return_value = {
                440: SteamAppDetails(app_id=440, name="TF2", age_ratings=(("PEGI", "18"), ("ESRB", "E"))),
            }
            thread.configure_steam([(440, "TF2")], enrichment_db.db_path, "test_key")
            thread.run()

        from steam_library_manager.core.database import Database

        db = Database(enrichment_db.db_path)
        row = db.conn.execute("SELECT pegi_rating FROM games WHERE app_id = 440").fetchone()
        db.close()
        assert row[0] == "18"

    @patch("steam_library_manager.integrations.steam_web_api.requests.get")
    def test_pegi_empty_ratings_no_update(self, mock_get: MagicMock, enrichment_db) -> None:
        """Empty age_ratings tuple does not write to DB."""
        from steam_library_manager.integrations.steam_web_api import SteamAppDetails

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"store_items": []}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        thread = EnrichmentThread()
        finished_spy = MagicMock()
        thread.finished_enrichment.connect(finished_spy)

        with patch("steam_library_manager.integrations.steam_web_api.SteamWebAPI.get_app_details_batch") as mock_batch:
            mock_batch.return_value = {
                440: SteamAppDetails(app_id=440, name="TF2", age_ratings=()),
            }
            thread.configure_steam([(440, "TF2")], enrichment_db.db_path, "test_key")
            thread.run()

        from steam_library_manager.core.database import Database

        db = Database(enrichment_db.db_path)
        row = db.conn.execute("SELECT pegi_rating FROM games WHERE app_id = 440").fetchone()
        db.close()
        assert row[0] == "" or row[0] is None

    @patch("steam_library_manager.integrations.steam_web_api.requests.get")
    def test_pegi_writes_all_ratings_to_age_ratings_table(self, mock_get: MagicMock, enrichment_db) -> None:
        """All rating systems from batch response are written to age_ratings table."""
        from steam_library_manager.integrations.steam_web_api import SteamAppDetails

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"store_items": []}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        thread = EnrichmentThread()
        finished_spy = MagicMock()
        thread.finished_enrichment.connect(finished_spy)

        with patch("steam_library_manager.integrations.steam_web_api.SteamWebAPI.get_app_details_batch") as mock_batch:
            mock_batch.return_value = {
                440: SteamAppDetails(app_id=440, name="TF2", age_ratings=(("PEGI", "16"), ("ESRB", "T"))),
            }
            thread.configure_steam([(440, "TF2")], enrichment_db.db_path, "test_key")
            thread.run()

        from steam_library_manager.core.database import Database

        db = Database(enrichment_db.db_path)
        rows = db.conn.execute(
            "SELECT rating_system, rating_value FROM age_ratings WHERE app_id = 440 ORDER BY rating_system"
        ).fetchall()
        db.close()
        ratings = [(row[0], row[1]) for row in rows]
        assert len(ratings) == 2
        assert ("ESRB", "T") in ratings
        assert ("PEGI", "16") in ratings


class TestPEGIGapFiller:
    """Tests for PEGI gap filler (skipping already-rated games)."""

    def test_pegi_gap_filler_skips_already_rated(self, enrichment_db) -> None:
        """PEGIEnrichmentThread skips games with existing pegi_rating."""
        from steam_library_manager.services.enrichment.pegi_enrichment_service import PEGIEnrichmentThread

        enrichment_db.conn.execute("UPDATE games SET pegi_rating = '12' WHERE app_id = 440")
        enrichment_db.conn.commit()

        thread = PEGIEnrichmentThread()
        thread._db = enrichment_db
        thread._scraper = MagicMock()
        thread._force_refresh = False

        result = thread._process_item((440, "TF2"))
        assert result is True
        thread._scraper.fetch_age_rating.assert_not_called()

    def test_pegi_gap_filler_fetches_unrated(self, enrichment_db) -> None:
        """PEGIEnrichmentThread fetches rating for games without pegi_rating."""
        from steam_library_manager.services.enrichment.pegi_enrichment_service import PEGIEnrichmentThread

        thread = PEGIEnrichmentThread()
        thread._db = enrichment_db
        thread._scraper = MagicMock()
        thread._scraper.fetch_age_rating.return_value = "18"
        thread._scraper.cache_dir.parent = Path("/tmp")
        thread._force_refresh = False

        result = thread._process_item((440, "TF2"))
        assert result is True
        thread._scraper.fetch_age_rating.assert_called_once_with("440")

    def test_pegi_gap_filler_force_refresh_ignores_existing(self, enrichment_db) -> None:
        """PEGIEnrichmentThread re-fetches with force_refresh even if rated."""
        from steam_library_manager.services.enrichment.pegi_enrichment_service import PEGIEnrichmentThread

        enrichment_db.conn.execute("UPDATE games SET pegi_rating = '12' WHERE app_id = 440")
        enrichment_db.conn.commit()

        thread = PEGIEnrichmentThread()
        thread._db = enrichment_db
        thread._scraper = MagicMock()
        thread._scraper.fetch_age_rating.return_value = "16"
        thread._scraper.cache_dir.parent.__truediv__ = MagicMock(return_value=MagicMock())
        thread._force_refresh = True

        result = thread._process_item((440, "TF2"))
        assert result is True
        thread._scraper.fetch_age_rating.assert_called_once()


class TestSteamAPIEnrichment:
    """Tests for Steam API enrichment via EnrichmentThread."""

    @patch("steam_library_manager.integrations.steam_web_api.requests.get")
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
