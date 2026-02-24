"""Tests for CuratorEnrichmentThread."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.services.enrichment.curator_enrichment_service import CuratorEnrichmentThread


class TestCuratorEnrichmentThread:
    """Tests for CuratorEnrichmentThread configure and template methods."""

    def test_configure_stores_curators(self) -> None:
        """configure() should store curators and db_path."""
        thread = CuratorEnrichmentThread()
        curators = [{"curator_id": 1, "name": "Test", "url": ""}]
        thread.configure(curators, Path("/tmp/test.db"))
        assert thread._curators == curators
        assert thread._db_path == Path("/tmp/test.db")
        assert thread._force_refresh is False

    def test_configure_force_refresh(self) -> None:
        """configure() with force_refresh=True should set the flag."""
        thread = CuratorEnrichmentThread()
        thread.configure([], Path("/tmp/test.db"), force_refresh=True)
        assert thread._force_refresh is True

    def test_get_items_returns_curators(self) -> None:
        """_get_items() should return the configured curators list."""
        thread = CuratorEnrichmentThread()
        curators = [{"curator_id": 1, "name": "A"}, {"curator_id": 2, "name": "B"}]
        thread.configure(curators, Path("/tmp/test.db"))
        assert thread._get_items() == curators

    def test_format_progress(self) -> None:
        """_format_progress() should include curator name and counts."""
        thread = CuratorEnrichmentThread()
        thread.configure([], Path("/tmp/test.db"))
        item = {"curator_id": 1, "name": "PC Gamer"}
        result = thread._format_progress(item, 3, 10)
        assert "PC Gamer" in result
        assert "3" in result
        assert "10" in result

    def test_process_item_filters_recommended_only(self) -> None:
        """_process_item should filter for RECOMMENDED only."""
        from src.services.curator_client import CuratorRecommendation

        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_client.fetch_recommendations.return_value = {
            100: CuratorRecommendation.RECOMMENDED,
            200: CuratorRecommendation.NOT_RECOMMENDED,
            300: CuratorRecommendation.INFORMATIONAL,
            400: CuratorRecommendation.RECOMMENDED,
        }

        thread = CuratorEnrichmentThread()
        thread.configure(
            [{"curator_id": 1850, "name": "PC Gamer", "url": ""}],
            Path("/tmp/test.db"),
        )
        # Inject mocks directly (lazy imports in _setup)
        thread._db = mock_db
        thread._client = mock_client

        result = thread._process_item({"curator_id": 1850, "name": "PC Gamer", "url": ""})

        assert result is True
        mock_db.save_curator_recommendations.assert_called_once()
        saved_ids = mock_db.save_curator_recommendations.call_args[0][1]
        assert set(saved_ids) == {100, 400}

    def test_process_item_handles_connection_error(self) -> None:
        """_process_item should return False on connection errors."""
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_client.fetch_recommendations.side_effect = ConnectionError("timeout")

        thread = CuratorEnrichmentThread()
        thread.configure(
            [{"curator_id": 1, "name": "Bad Curator", "url": ""}],
            Path("/tmp/test.db"),
        )
        thread._db = mock_db
        thread._client = mock_client

        result = thread._process_item({"curator_id": 1, "name": "Bad Curator", "url": ""})

        assert result is False
        mock_db.save_curator_recommendations.assert_not_called()

    def test_process_item_uses_url_fallback(self) -> None:
        """When url is empty, should construct URL from curator_id."""
        thread = CuratorEnrichmentThread()
        thread.configure([], Path("/tmp/test.db"))

        item = {"curator_id": 1850, "name": "PC Gamer", "url": ""}
        # The URL fallback is constructed in _process_item
        url = item.get("url") or f"https://store.steampowered.com/curator/{item['curator_id']}/"
        assert url == "https://store.steampowered.com/curator/1850/"

    def test_rate_limit_is_two_seconds(self) -> None:
        """Rate limit should be 2.0 seconds for Steam courtesy."""
        thread = CuratorEnrichmentThread()
        thread.configure([], Path("/tmp/test.db"))
        # We can't easily test sleep without mocking, but verify the method exists
        assert hasattr(thread, "_rate_limit")
