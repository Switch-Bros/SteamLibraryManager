"""Tests for PEGIEnrichmentThread."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.enrichment.pegi_enrichment_service import PEGIEnrichmentThread


class TestPEGIEnrichmentConfig:
    """Tests for PEGIEnrichmentThread configuration."""

    def test_configure_stores_games(self) -> None:
        """Configured games list is stored correctly."""
        thread = PEGIEnrichmentThread()
        games = [(1, "Game A"), (2, "Game B")]
        thread.configure(games, MagicMock())
        assert thread._games is games

    def test_configure_default_force_refresh_false(self) -> None:
        """Default force_refresh is False."""
        thread = PEGIEnrichmentThread()
        thread.configure([], MagicMock())
        assert thread._force_refresh is False

    def test_configure_force_refresh_true(self) -> None:
        """force_refresh=True is stored correctly."""
        thread = PEGIEnrichmentThread()
        thread.configure([], MagicMock(), force_refresh=True)
        assert thread._force_refresh is True

    def test_configure_default_language(self) -> None:
        """Default language is 'en'."""
        thread = PEGIEnrichmentThread()
        thread.configure([], MagicMock())
        assert thread._language == "en"

    def test_configure_custom_language(self) -> None:
        """Custom language is stored correctly."""
        thread = PEGIEnrichmentThread()
        thread.configure([], MagicMock(), language="de")
        assert thread._language == "de"

    def test_cancel_sets_flag(self) -> None:
        """cancel() sets the _cancelled flag."""
        thread = PEGIEnrichmentThread()
        assert not thread._cancelled
        thread.cancel()
        assert thread._cancelled

    def test_get_items_returns_games(self) -> None:
        """_get_items() returns the configured games list."""
        thread = PEGIEnrichmentThread()
        games = [(440, "TF2"), (730, "CS2")]
        thread.configure(games, MagicMock())
        assert thread._get_items() == games

    def test_get_items_empty_list(self) -> None:
        """_get_items() returns empty list when no games configured."""
        thread = PEGIEnrichmentThread()
        thread.configure([], MagicMock())
        assert thread._get_items() == []
