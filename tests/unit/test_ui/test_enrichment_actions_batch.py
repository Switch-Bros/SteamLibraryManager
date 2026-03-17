"""Tests for batch enrichment operations and EnrichAllCoordinator.

Covers the batch result dialog flow, force-refresh callback pattern,
and the EnrichAllCoordinator's track management.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from steam_library_manager.services.enrichment.enrich_all_coordinator import (
    TRK_DECK,
    TRK_HLTB,
    TRK_PDB,
    TRK_STEAM,
    TRK_TAGS,
    EnrichAllCoordinator,
)

# ---------------------------------------------------------------------------
# EnrichAllCoordinator: basic lifecycle
# ---------------------------------------------------------------------------


class TestEnrichAllCoordinator:
    """Tests for EnrichAllCoordinator track management."""

    def _make_coordinator(self, tmp_path: Path) -> EnrichAllCoordinator:
        """Creates a coordinator with minimal configuration."""
        coord = EnrichAllCoordinator()
        coord.configure(
            db_path=tmp_path / "test.db",
            api_key="test-key",
            steam_id="76561198000000000",
            steam_path=tmp_path / "steam",
            games_deck=[MagicMock()],
            games_db=[(1, "Game A"), (2, "Game B")],
            hltb_client=MagicMock(),
            language="en",
            cache_dir=tmp_path / "cache",
        )
        return coord

    def test_initial_state(self) -> None:
        """Coordinator starts with no threads and no results."""
        coord = EnrichAllCoordinator()
        assert coord._pending == 0
        assert coord._results == {}
        assert coord._cancelled is False

    def test_cancel_sets_flag(self, tmp_path: Path) -> None:
        """Cancel sets the cancellation flag."""
        coord = self._make_coordinator(tmp_path)
        coord.cancel()
        assert coord._cancelled is True

    def test_track_completion_decrements_counter(self, tmp_path: Path) -> None:
        """Each track completion decrements the pending counter."""
        coord = self._make_coordinator(tmp_path)
        coord._pending = 3

        finished_signals: list[dict] = []
        coord.all_finished.connect(lambda r: finished_signals.append(r))

        coord._on_trk_done(TRK_HLTB, 5, 0)
        assert coord._pending == 2
        assert len(finished_signals) == 0

        coord._on_trk_done(TRK_PDB, 3, 1)
        assert coord._pending == 1
        assert len(finished_signals) == 0

        coord._on_trk_done(TRK_DECK, 4, 0)
        assert coord._pending == 0
        assert len(finished_signals) == 1

    def test_all_tracks_complete_emits_all_finished(self, tmp_path: Path) -> None:
        """When all tracks complete, all_finished signal is emitted."""
        coord = self._make_coordinator(tmp_path)
        coord._pending = 2

        results_received: list[dict] = []
        coord.all_finished.connect(lambda r: results_received.append(r))

        coord._on_trk_done(TRK_HLTB, 10, 0)
        coord._on_trk_done(TRK_DECK, 5, 2)

        assert len(results_received) == 1
        result = results_received[0]
        assert result[TRK_HLTB] == (10, 0)
        assert result[TRK_DECK] == (5, 2)

    def test_track_error_still_completes(self, tmp_path: Path) -> None:
        """Track errors still decrement the counter and emit track_finished."""
        coord = self._make_coordinator(tmp_path)
        coord._pending = 1

        finished: list[tuple[str, int, int]] = []
        coord.track_finished.connect(lambda t, s, f: finished.append((t, s, f)))

        all_done: list[dict] = []
        coord.all_finished.connect(lambda r: all_done.append(r))

        coord._on_trk_err(TRK_PDB, "API down")

        assert len(finished) == 1
        assert finished[0] == (TRK_PDB, 0, -1)
        assert len(all_done) == 1
        assert coord._results[TRK_PDB] == (0, -1)

    def test_skipped_tracks_emit_minus_one(self, tmp_path: Path) -> None:
        """Tracks without prerequisites emit success=-1 (skipped)."""
        coord = EnrichAllCoordinator()
        coord.configure(
            db_path=tmp_path / "test.db",
            api_key="",  # No API key → Steam + Achievements skipped
            steam_id="",
            steam_path=None,  # No steam path → Tags skipped
            games_deck=[],  # No games → Deck skipped
            games_db=[(1, "Game")],
            hltb_client=None,  # No HLTB → HLTB skipped
            language="en",
            cache_dir=tmp_path / "cache",
        )

        finished: list[tuple[str, int, int]] = []
        coord.track_finished.connect(lambda t, s, f: finished.append((t, s, f)))

        # Mock _run_protondb to avoid creating real/mock threads
        with patch.object(coord, "_run_protondb"):
            coord.start()

        # Tags emits skipped (-1)
        tags_finished = [f for f in finished if f[0] == TRK_TAGS]
        assert len(tags_finished) == 1
        assert tags_finished[0][1] == -1

        # Steam, HLTB, Deck emit skipped
        for track in [TRK_STEAM, TRK_HLTB, TRK_DECK]:
            track_finished = [f for f in finished if f[0] == track]
            assert len(track_finished) == 1
            assert track_finished[0][1] == -1

    def test_steam_track_chains_metadata_then_achievements(self, tmp_path: Path) -> None:
        """Steam track runs metadata first, then achievements."""
        coord = self._make_coordinator(tmp_path)
        coord._pending = 1

        finished: list[tuple[str, int, int]] = []
        coord.track_finished.connect(lambda t, s, f: finished.append((t, s, f)))

        # Mock achievement phase to avoid creating threads
        with patch.object(coord, "_run_achievements") as mock_ach:
            coord._on_steam_meta_done(10, 2)

        # Metadata result stored separately
        assert f"{TRK_STEAM}_metadata" in coord._results
        assert coord._results[f"{TRK_STEAM}_metadata"] == (10, 2)
        # Achievement phase was triggered
        mock_ach.assert_called_once_with(10, 2)

    def test_steam_track_done_combines_counts(self, tmp_path: Path) -> None:
        """Steam track done handler sums metadata + achievement counts."""
        coord = self._make_coordinator(tmp_path)
        coord._pending = 1

        finished: list[tuple[str, int, int]] = []
        coord.track_finished.connect(lambda t, s, f: finished.append((t, s, f)))

        all_done: list[dict] = []
        coord.all_finished.connect(lambda r: all_done.append(r))

        coord._on_steam_done(10, 2, 8, 1)

        assert len(finished) == 1
        assert finished[0] == (TRK_STEAM, 18, 3)
        assert len(all_done) == 1
        assert coord._results[TRK_STEAM] == (18, 3)

    def test_tags_error_continues_to_parallel_tracks(self, tmp_path: Path) -> None:
        """Tag import error should still start parallel tracks."""
        coord = self._make_coordinator(tmp_path)

        finished: list[tuple[str, int, int]] = []
        coord.track_finished.connect(lambda t, s, f: finished.append((t, s, f)))

        # Mock _run_parallel to avoid creating threads
        with patch.object(coord, "_run_parallel") as mock_parallel:
            coord._on_tags_err("appinfo.vdf not found")

        # Tags should be marked as failed
        tags_result = [f for f in finished if f[0] == TRK_TAGS]
        assert len(tags_result) == 1
        assert tags_result[0] == (TRK_TAGS, 0, 1)
        # Parallel tracks still started after error
        mock_parallel.assert_called_once()


# ---------------------------------------------------------------------------
# EnrichmentActions: enrich_all confirm flow
# ---------------------------------------------------------------------------


class TestEnrichAllConfirmFlow:
    """Tests for the start_enrich_all confirmation flow."""

    @patch("steam_library_manager.config.config")
    @patch("steam_library_manager.ui.actions.enrichment_actions.UIHelper")
    def test_enrich_all_confirm_cancelled(
        self,
        mock_helper: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        """User cancelling confirm dialog prevents enrichment start."""
        mock_config.STEAM_API_KEY = "test-key"
        mock_config.STEAM_USER_ID = "76561198000000000"
        mock_helper.confirm.return_value = False

        mock_mw = MagicMock()
        mock_mw.game_manager.get_real_games.return_value = [MagicMock()]

        mock_db = MagicMock()
        mock_db.get_all_game_ids.return_value = [(1, "Game")]

        from steam_library_manager.ui.actions.enrichment_actions import EnrichmentActions

        actions = EnrichmentActions(mock_mw)

        with patch.object(actions, "_open_database", return_value=mock_db):
            actions.start_enrich_all()

        mock_helper.confirm.assert_called_once()

    @patch("steam_library_manager.config.config")
    @patch("steam_library_manager.ui.actions.enrichment_actions.UIHelper")
    def test_enrich_all_no_api_key(
        self,
        mock_helper: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        """Missing API key shows warning and opens settings."""
        mock_config.STEAM_API_KEY = ""

        mock_mw = MagicMock()
        mock_mw.game_manager = MagicMock()

        from steam_library_manager.ui.actions.enrichment_actions import EnrichmentActions

        actions = EnrichmentActions(mock_mw)

        with patch.object(actions, "_open_settings_api_tab") as mock_settings:
            actions.start_enrich_all()

        mock_helper.show_warning.assert_called_once()
        mock_settings.assert_called_once()
