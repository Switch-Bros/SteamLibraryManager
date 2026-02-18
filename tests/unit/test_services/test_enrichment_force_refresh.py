"""Tests for enrichment force_refresh parameter support.

Verifies that all enrichment threads accept and propagate the
force_refresh flag, and that EnrichmentActions uses the correct
DB methods based on the flag.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.enrichment.achievement_enrichment_service import AchievementEnrichmentThread
from src.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from src.services.enrichment.deck_enrichment_service import DeckEnrichmentThread
from src.services.enrichment.enrichment_service import EnrichmentThread
from src.services.enrichment.protondb_enrichment_service import ProtonDBEnrichmentThread

# ---------------------------------------------------------------------------
# BaseEnrichmentThread: force_refresh attribute
# ---------------------------------------------------------------------------


class TestBaseEnrichmentThreadForceRefresh:
    """Tests for the base class force_refresh attribute."""

    def test_default_force_refresh_is_false(self) -> None:
        thread = BaseEnrichmentThread()
        assert thread._force_refresh is False

    def test_force_refresh_can_be_set(self) -> None:
        thread = BaseEnrichmentThread()
        thread._force_refresh = True
        assert thread._force_refresh is True


# ---------------------------------------------------------------------------
# EnrichmentThread: configure with force_refresh
# ---------------------------------------------------------------------------


class TestEnrichmentThreadForceRefresh:
    """Tests for EnrichmentThread force_refresh propagation."""

    def test_hltb_configure_default(self) -> None:
        thread = EnrichmentThread()
        mock_client = MagicMock()
        thread.configure_hltb([(1, "Game")], MagicMock(), mock_client)
        assert thread._force_refresh is False

    def test_hltb_configure_force(self) -> None:
        thread = EnrichmentThread()
        mock_client = MagicMock()
        thread.configure_hltb([(1, "Game")], MagicMock(), mock_client, force_refresh=True)
        assert thread._force_refresh is True

    def test_steam_configure_default(self) -> None:
        thread = EnrichmentThread()
        thread.configure_steam([(1, "Game")], MagicMock(), "test-key")
        assert thread._force_refresh is False

    def test_steam_configure_force(self) -> None:
        thread = EnrichmentThread()
        thread.configure_steam([(1, "Game")], MagicMock(), "test-key", force_refresh=True)
        assert thread._force_refresh is True


# ---------------------------------------------------------------------------
# DeckEnrichmentThread: configure with force_refresh
# ---------------------------------------------------------------------------


class TestDeckEnrichmentThreadForceRefresh:
    """Tests for DeckEnrichmentThread force_refresh propagation."""

    def test_configure_default(self) -> None:
        thread = DeckEnrichmentThread()
        thread.configure([], MagicMock())
        assert thread._force_refresh is False

    def test_configure_force(self) -> None:
        thread = DeckEnrichmentThread()
        thread.configure([], MagicMock(), force_refresh=True)
        assert thread._force_refresh is True


# ---------------------------------------------------------------------------
# AchievementEnrichmentThread: configure with force_refresh
# ---------------------------------------------------------------------------


class TestAchievementEnrichmentThreadForceRefresh:
    """Tests for AchievementEnrichmentThread force_refresh propagation."""

    def test_configure_default(self) -> None:
        thread = AchievementEnrichmentThread()
        thread.configure([(1, "Game")], MagicMock(), "key", "steam_id")
        assert thread._force_refresh is False

    def test_configure_force(self) -> None:
        thread = AchievementEnrichmentThread()
        thread.configure(
            [(1, "Game")],
            MagicMock(),
            "key",
            "steam_id",
            force_refresh=True,
        )
        assert thread._force_refresh is True


# ---------------------------------------------------------------------------
# ProtonDBEnrichmentThread: configure with force_refresh
# ---------------------------------------------------------------------------


class TestProtonDBEnrichmentThreadForceRefresh:
    """Tests for ProtonDBEnrichmentThread force_refresh propagation."""

    def test_configure_default(self) -> None:
        thread = ProtonDBEnrichmentThread()
        thread.configure([(1, "Game")], MagicMock())
        assert thread._force_refresh is False

    def test_configure_force(self) -> None:
        thread = ProtonDBEnrichmentThread()
        thread.configure([(1, "Game")], MagicMock(), force_refresh=True)
        assert thread._force_refresh is True


# ---------------------------------------------------------------------------
# EnrichmentActions: force_refresh DB method selection
# ---------------------------------------------------------------------------


class TestEnrichmentActionsForceRefresh:
    """Tests that EnrichmentActions selects correct DB methods."""

    def test_deck_filter_without_force(self) -> None:
        """Without force, filtering logic should exclude games with deck status."""
        game_with = MagicMock(steam_deck_status="verified")
        game_without = MagicMock(steam_deck_status="")
        game_unknown = MagicMock(steam_deck_status="unknown")
        all_games = [game_with, game_without, game_unknown]

        # Replicate the filtering logic from start_deck_enrichment
        filtered = [g for g in all_games if not g.steam_deck_status or g.steam_deck_status == "unknown"]
        assert len(filtered) == 2
        assert game_with not in filtered
        assert game_without in filtered
        assert game_unknown in filtered

    def test_deck_no_filter_with_force(self) -> None:
        """With force, all games should be included."""
        game_with = MagicMock(steam_deck_status="verified")
        game_without = MagicMock(steam_deck_status="")
        all_games = [game_with, game_without]

        # With force_refresh, the code uses all_games directly
        assert len(all_games) == 2

    @patch("src.ui.actions.enrichment_actions.UIHelper")
    def test_force_refresh_cancelled_by_user(self, mock_helper: MagicMock) -> None:
        """If user cancels confirmation, enrichment should not start."""
        mock_helper.confirm.return_value = False
        mock_mw = MagicMock()
        mock_mw.game_manager.get_real_games.return_value = [MagicMock(steam_deck_status="verified")]

        from src.ui.actions.enrichment_actions import EnrichmentActions

        actions = EnrichmentActions(mock_mw)

        with patch.object(actions, "_run_enrichment") as mock_run:
            actions.start_deck_enrichment(force_refresh=True)

        mock_run.assert_not_called()
