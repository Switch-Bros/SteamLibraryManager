"""Tests for the library health check service and thread."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.library_health_service import HealthReport, StoreCheckResult


class TestStoreCheckResult:
    """Tests for the StoreCheckResult frozen dataclass."""

    def test_store_check_result_frozen(self) -> None:
        """StoreCheckResult should be immutable."""
        result = StoreCheckResult(app_id=440, name="TF2", status="available", details="HTTP 200")
        with pytest.raises(AttributeError):
            result.status = "removed"  # type: ignore[misc]

    def test_store_check_result_equality(self) -> None:
        """Two StoreCheckResults with same values should be equal."""
        a = StoreCheckResult(app_id=440, name="TF2", status="delisted", details="HTTP 302")
        b = StoreCheckResult(app_id=440, name="TF2", status="delisted", details="HTTP 302")
        assert a == b


class TestHealthReport:
    """Tests for the HealthReport dataclass."""

    def test_count_total_issues_empty(self) -> None:
        """Empty report should have zero issues."""
        report = HealthReport(total_games=100)
        assert report.count_total_issues() == 0

    def test_count_total_issues_all_categories(self) -> None:
        """Should sum issues across all categories."""
        report = HealthReport(
            store_unavailable=[
                StoreCheckResult(app_id=1, name="A", status="removed", details=""),
                StoreCheckResult(app_id=2, name="B", status="delisted", details=""),
            ],
            missing_artwork=[(3, "C")],
            missing_metadata=[(4, "D"), (5, "E")],
            ghost_apps=[(6, "F")],
            stale_hltb=10,
            stale_protondb=5,
            total_games=200,
        )
        assert report.count_total_issues() == 2 + 1 + 2 + 1 + 10 + 5

    def test_default_values(self) -> None:
        """All list/int fields should default to empty/zero."""
        report = HealthReport()
        assert report.store_unavailable == []
        assert report.missing_artwork == []
        assert report.missing_metadata == []
        assert report.ghost_apps == []
        assert report.stale_hltb == 0
        assert report.stale_protondb == 0
        assert report.total_games == 0


class TestLibraryHealthThread:
    """Tests for the LibraryHealthThread."""

    def test_batch_missing_detection(self) -> None:
        """IDs not returned by _fetch_batch should be flagged as missing."""
        from src.services.library_health_thread import LibraryHealthThread

        thread = LibraryHealthThread(
            games=[(440, "TF2"), (570, "Dota 2"), (730, "CS2")],
            api_key="test_key",
            db_path=Path("/tmp/test.db"),
        )

        with patch("src.integrations.steam_web_api.SteamWebAPI") as mock_api_cls:
            mock_api = MagicMock()
            mock_api_cls.return_value = mock_api
            # Only return 440 and 730 — 570 is "missing"
            mock_api._fetch_batch.return_value = [
                {"appid": 440},
                {"appid": 730},
            ]

            missing = thread._check_store_batch([440, 570, 730])
            assert missing == [570]

    def test_batch_api_error_graceful(self) -> None:
        """API errors during batch check should not crash, just log."""
        from src.services.library_health_thread import LibraryHealthThread

        thread = LibraryHealthThread(
            games=[(440, "TF2")],
            api_key="test_key",
            db_path=Path("/tmp/test.db"),
        )

        with patch("src.integrations.steam_web_api.SteamWebAPI") as mock_api_cls:
            mock_api = MagicMock()
            mock_api_cls.return_value = mock_api
            mock_api._fetch_batch.side_effect = Exception("API timeout")

            missing = thread._check_store_batch([440])
            # Error is swallowed, all IDs treated as missing
            assert missing == [440]

    def test_batch_invalid_api_key(self) -> None:
        """Invalid API key should return empty list (no crash)."""
        from src.services.library_health_thread import LibraryHealthThread

        thread = LibraryHealthThread(
            games=[(440, "TF2")],
            api_key="bad_key",
            db_path=Path("/tmp/test.db"),
        )

        with patch(
            "src.integrations.steam_web_api.SteamWebAPI",
            side_effect=ValueError("Invalid key"),
        ):
            missing = thread._check_store_batch([440])
            assert missing == []

    def test_detail_removed_404(self) -> None:
        """HTTP 404 should classify as 'removed'."""
        from src.services.library_health_thread import LibraryHealthThread

        thread = LibraryHealthThread(
            games=[(440, "TF2")],
            api_key="test",
            db_path=Path("/tmp/test.db"),
        )

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("src.services.library_health_thread.requests.get", return_value=mock_response):
            with patch("src.services.library_health_thread.time.sleep"):
                results = thread._check_store_detail([440], {440: "TF2"})

        assert len(results) == 1
        assert results[0].status == "removed"
        assert results[0].app_id == 440

    def test_detail_age_gate(self) -> None:
        """URL containing 'agecheck' should classify as 'age_gate'."""
        from src.services.library_health_thread import LibraryHealthThread

        thread = LibraryHealthThread(
            games=[(440, "TF2")],
            api_key="test",
            db_path=Path("/tmp/test.db"),
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://store.steampowered.com/agecheck/app/440/"
        mock_response.text = "<html>Age verification required</html>"

        with patch("src.services.library_health_thread.requests.get", return_value=mock_response):
            with patch("src.services.library_health_thread.time.sleep"):
                results = thread._check_store_detail([440], {440: "TF2"})

        assert results[0].status == "age_gate"

    def test_detail_geo_locked(self) -> None:
        """Page containing geo-keywords should classify as 'geo_locked'."""
        from src.services.library_health_thread import LibraryHealthThread

        thread = LibraryHealthThread(
            games=[(440, "TF2")],
            api_key="test",
            db_path=Path("/tmp/test.db"),
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://store.steampowered.com/app/440/"
        mock_response.text = "<html>This product is not available in your country</html>"

        with patch("src.services.library_health_thread.requests.get", return_value=mock_response):
            with patch("src.services.library_health_thread.time.sleep"):
                results = thread._check_store_detail([440], {440: "TF2"})

        assert results[0].status == "geo_locked"

    def test_detail_delisted(self) -> None:
        """Redirect to different URL should classify as 'delisted'."""
        from src.services.library_health_thread import LibraryHealthThread

        thread = LibraryHealthThread(
            games=[(440, "TF2")],
            api_key="test",
            db_path=Path("/tmp/test.db"),
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://store.steampowered.com/"
        mock_response.text = "<html>Steam Store</html>"

        with patch("src.services.library_health_thread.requests.get", return_value=mock_response):
            with patch("src.services.library_health_thread.time.sleep"):
                results = thread._check_store_detail([440], {440: "TF2"})

        assert results[0].status == "delisted"

    def test_cancellation_stops_batch(self) -> None:
        """Cancelling should stop batch processing and return empty list."""
        from src.services.library_health_thread import LibraryHealthThread

        thread = LibraryHealthThread(
            games=[(440, "TF2")],
            api_key="test_key",
            db_path=Path("/tmp/test.db"),
        )
        thread.cancel()

        with patch("src.integrations.steam_web_api.SteamWebAPI") as mock_api_cls:
            mock_api = MagicMock()
            mock_api_cls.return_value = mock_api

            missing = thread._check_store_batch([440])
            assert missing == []
            mock_api._fetch_batch.assert_not_called()

    def test_cancellation_stops_detail(self) -> None:
        """Cancelling should stop detail checking and return partial results."""
        from src.services.library_health_thread import LibraryHealthThread

        thread = LibraryHealthThread(
            games=[(440, "TF2")],
            api_key="test",
            db_path=Path("/tmp/test.db"),
        )
        thread.cancel()

        results = thread._check_store_detail([440, 570], {440: "TF2", 570: "Dota"})
        assert results == []


class TestDatabaseHealthMethods:
    """Tests for the health-check database query methods."""

    @pytest.fixture
    def health_db(self, tmp_path: Path):
        """Creates a database with test data for health checks."""
        from src.core.database import Database

        db_path = tmp_path / "health_test.db"
        db = Database(db_path)

        # Insert games — some with artwork, some without
        for app_id, name in [(440, "TF2"), (570, "Dota 2"), (730, "CS2")]:
            db.conn.execute(
                "INSERT INTO games (app_id, name, app_type, developer, platforms, created_at, updated_at) "
                "VALUES (?, ?, 'game', '', '[]', 0, 0)",
                (app_id, name),
            )

        # Only 440 has custom artwork
        db.conn.execute(
            "INSERT INTO custom_artwork (app_id, artwork_type, source, source_url, set_at) "
            "VALUES (440, 'grid_p', 'steamgriddb', 'https://example.com/440.jpg', 0)"
        )

        # HLTB data — one fresh, one stale
        now = int(time.time())
        stale = now - (31 * 86400)  # 31 days old
        db.conn.execute(
            "INSERT INTO hltb_data (app_id, main_story, main_extras, completionist, last_updated) "
            "VALUES (440, 10.0, 20.0, 30.0, ?)",
            (now,),
        )
        db.conn.execute(
            "INSERT INTO hltb_data (app_id, main_story, main_extras, completionist, last_updated) "
            "VALUES (570, 100.0, 200.0, 300.0, ?)",
            (stale,),
        )

        # ProtonDB data — one fresh, one stale
        proton_stale = now - (8 * 86400)  # 8 days old
        db.conn.execute(
            "INSERT INTO protondb_ratings (app_id, tier, confidence, last_updated) " "VALUES (440, 'gold', 'good', ?)",
            (now,),
        )
        db.conn.execute(
            "INSERT INTO protondb_ratings (app_id, tier, confidence, last_updated) "
            "VALUES (570, 'platinum', 'strong', ?)",
            (proton_stale,),
        )

        db.conn.commit()
        yield db
        db.close()

    def test_get_games_missing_artwork(self, health_db) -> None:
        """Should return games without entries in custom_artwork."""
        missing = health_db.get_games_missing_artwork()
        app_ids = [app_id for app_id, _ in missing]
        assert 440 not in app_ids  # has artwork
        assert 570 in app_ids
        assert 730 in app_ids

    def test_get_stale_hltb_count(self, health_db) -> None:
        """Should count HLTB entries older than max_age_days."""
        assert health_db.get_stale_hltb_count(max_age_days=30) == 1
        assert health_db.get_stale_hltb_count(max_age_days=365) == 0

    def test_get_stale_protondb_count(self, health_db) -> None:
        """Should count ProtonDB entries older than max_age_days."""
        assert health_db.get_stale_protondb_count(max_age_days=7) == 1
        assert health_db.get_stale_protondb_count(max_age_days=365) == 0
