"""Tests for the ProtonDB API client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.integrations.protondb_api import ProtonDBClient, ProtonDBResult


class TestProtonDBResult:
    """Tests for the ProtonDBResult frozen dataclass."""

    def test_create_with_all_fields(self) -> None:
        result = ProtonDBResult(
            tier="gold",
            confidence="strong",
            trending_tier="platinum",
            score=0.85,
            best_reported="platinum",
        )
        assert result.tier == "gold"
        assert result.confidence == "strong"
        assert result.trending_tier == "platinum"
        assert result.score == 0.85
        assert result.best_reported == "platinum"

    def test_create_with_defaults(self) -> None:
        result = ProtonDBResult(tier="silver")
        assert result.tier == "silver"
        assert result.confidence == ""
        assert result.trending_tier == ""
        assert result.score == 0.0
        assert result.best_reported == ""

    def test_frozen_immutability(self) -> None:
        result = ProtonDBResult(tier="gold")
        with pytest.raises(AttributeError):
            result.tier = "platinum"  # type: ignore[misc]


class TestProtonDBClientGetRating:
    """Tests for ProtonDBClient.get_rating()."""

    @patch("src.integrations.protondb_api.requests.Session")
    def test_get_rating_success(self, mock_session_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tier": "gold",
            "confidence": "strong",
            "trendingTier": "platinum",
            "score": 0.82,
            "bestReportedTier": "platinum",
        }
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session_cls.return_value = mock_session

        client = ProtonDBClient()
        result = client.get_rating(730)

        assert result is not None
        assert result.tier == "gold"
        assert result.confidence == "strong"
        assert result.trending_tier == "platinum"
        assert result.score == 0.82
        assert result.best_reported == "platinum"

    @patch("src.integrations.protondb_api.requests.Session")
    def test_get_rating_404_returns_none(self, mock_session_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session_cls.return_value = mock_session

        client = ProtonDBClient()
        result = client.get_rating(99999999)

        assert result is None

    @patch("src.integrations.protondb_api.requests.Session")
    def test_get_rating_network_error_returns_none(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.ConnectionError("Connection refused")
        mock_session_cls.return_value = mock_session

        client = ProtonDBClient()
        result = client.get_rating(730)

        assert result is None

    @patch("src.integrations.protondb_api.requests.Session")
    def test_get_rating_partial_response(self, mock_session_cls: MagicMock) -> None:
        """API returns only tier, missing optional fields."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tier": "borked"}
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session_cls.return_value = mock_session

        client = ProtonDBClient()
        result = client.get_rating(12345)

        assert result is not None
        assert result.tier == "borked"
        assert result.confidence == ""
        assert result.score == 0.0

    @patch("src.integrations.protondb_api.requests.Session")
    def test_get_rating_server_error_returns_none(self, mock_session_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session_cls.return_value = mock_session

        client = ProtonDBClient()
        result = client.get_rating(730)

        assert result is None


class TestProtonDBClientBatch:
    """Tests for ProtonDBClient.get_ratings_batch()."""

    @patch("src.integrations.protondb_api.requests.Session")
    @patch("src.integrations.protondb_api.time.sleep")
    def test_batch_returns_successful_results(self, mock_sleep: MagicMock, mock_session_cls: MagicMock) -> None:
        responses = []
        for tier in ("gold", "platinum"):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"tier": tier}
            responses.append(resp)

        mock_session = MagicMock()
        mock_session.get.side_effect = responses
        mock_session_cls.return_value = mock_session

        client = ProtonDBClient()
        results = client.get_ratings_batch([730, 440], delay=0.0)

        assert len(results) == 2
        assert results[730].tier == "gold"
        assert results[440].tier == "platinum"

    @patch("src.integrations.protondb_api.requests.Session")
    @patch("src.integrations.protondb_api.time.sleep")
    def test_batch_skips_failed_lookups(self, mock_sleep: MagicMock, mock_session_cls: MagicMock) -> None:
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"tier": "gold"}

        fail_resp = MagicMock()
        fail_resp.status_code = 404

        mock_session = MagicMock()
        mock_session.get.side_effect = [ok_resp, fail_resp]
        mock_session_cls.return_value = mock_session

        client = ProtonDBClient()
        results = client.get_ratings_batch([730, 99999], delay=0.0)

        assert len(results) == 1
        assert 730 in results
        assert 99999 not in results

    @patch("src.integrations.protondb_api.requests.Session")
    @patch("src.integrations.protondb_api.time.sleep")
    def test_batch_empty_list(self, mock_sleep: MagicMock, mock_session_cls: MagicMock) -> None:
        mock_session_cls.return_value = MagicMock()

        client = ProtonDBClient()
        results = client.get_ratings_batch([])

        assert results == {}


class TestProtonDBDatabaseCache:
    """Tests for ProtonDB database caching methods."""

    @pytest.fixture()
    def db(self, tmp_path):
        from src.core.database import Database

        return Database(tmp_path / "test.db")

    def test_upsert_and_get_cached(self, db) -> None:
        db.upsert_protondb(730, tier="gold", confidence="strong", score=0.8)
        db.commit()

        cached = db.get_cached_protondb(730)
        assert cached is not None
        assert cached["tier"] == "gold"
        assert cached["confidence"] == "strong"
        assert cached["score"] == 0.8

    def test_cache_miss_returns_none(self, db) -> None:
        cached = db.get_cached_protondb(99999)
        assert cached is None

    def test_expired_cache_returns_none(self, db) -> None:
        # Insert with a timestamp older than 7 days
        import time

        old_ts = int(time.time()) - (8 * 86400)
        db.conn.execute(
            "INSERT INTO protondb_ratings (app_id, tier, last_updated) VALUES (?, ?, ?)",
            (730, "gold", old_ts),
        )
        db.commit()

        cached = db.get_cached_protondb(730)
        assert cached is None

    def test_get_apps_without_protondb(self, db) -> None:
        # Insert a game
        db.conn.execute(
            "INSERT INTO games (app_id, name, app_type, created_at, updated_at) VALUES (?, ?, ?, 0, 0)",
            (730, "Counter-Strike 2", "game"),
        )
        db.conn.execute(
            "INSERT INTO games (app_id, name, app_type, created_at, updated_at) VALUES (?, ?, ?, 0, 0)",
            (440, "Team Fortress 2", "game"),
        )
        # Give only one a ProtonDB rating
        db.upsert_protondb(730, tier="gold")
        db.commit()

        missing = db.get_apps_without_protondb()
        assert len(missing) == 1
        assert missing[0][0] == 440

    def test_batch_get_protondb(self, db) -> None:
        db.upsert_protondb(730, tier="gold")
        db.upsert_protondb(440, tier="platinum")
        db.commit()

        result = db.batch_get_protondb([730, 440, 99999])
        assert result[730] == "gold"
        assert result[440] == "platinum"
        assert 99999 not in result
