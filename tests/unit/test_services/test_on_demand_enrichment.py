# tests/unit/test_services/test_on_demand_enrichment.py

"""Tests for on-demand enrichment in GameDetailService.

Covers needs_enrichment(), _fetch_hltb_data(), _fetch_achievement_data()
with mocked APIs to avoid real network calls. Also tests enricher
apply functions from game_detail_enrichers.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.game import Game
from src.services.game_detail_enrichers import (
    apply_achievement_data,
    apply_hltb_data,
)
from src.services.game_detail_service import GameDetailService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Returns a temporary cache directory."""
    d = tmp_path / "cache"
    d.mkdir()
    (d / "store_data").mkdir()
    return d


@pytest.fixture
def games() -> dict[str, Game]:
    """Returns a shared games dict with a test game."""
    return {
        "100": Game(
            app_id="100",
            name="Test Game",
            app_type="game",
        ),
    }


@pytest.fixture
def service(games: dict[str, Game], cache_dir: Path) -> GameDetailService:
    """Returns a GameDetailService instance."""
    return GameDetailService(games, cache_dir)


# ---------------------------------------------------------------------------
# needs_enrichment()
# ---------------------------------------------------------------------------


class TestNeedsEnrichment:
    """Tests for the needs_enrichment() method."""

    def test_needs_enrichment_no_developer(self, service: GameDetailService) -> None:
        """Returns True when developer is missing."""
        assert service.needs_enrichment("100") is True

    def test_needs_enrichment_no_proton(self, service: GameDetailService, games: dict) -> None:
        """Returns True when proton_db_rating is missing."""
        games["100"].developer = "Valve"
        assert service.needs_enrichment("100") is True

    def test_needs_enrichment_no_deck(self, service: GameDetailService, games: dict) -> None:
        """Returns True when steam_deck_status is missing."""
        games["100"].developer = "Valve"
        games["100"].proton_db_rating = "gold"
        assert service.needs_enrichment("100") is True

    def test_needs_enrichment_no_hltb(self, service: GameDetailService, games: dict) -> None:
        """Returns True when HLTB data is missing and not yet checked."""
        games["100"].developer = "Valve"
        games["100"].proton_db_rating = "gold"
        games["100"].steam_deck_status = "verified"
        assert service.needs_enrichment("100") is True

    def test_needs_enrichment_hltb_checked(self, service: GameDetailService, games: dict) -> None:
        """Returns False when HLTB was already checked (no data)."""
        games["100"].developer = "Valve"
        games["100"].proton_db_rating = "gold"
        games["100"].steam_deck_status = "verified"
        service._hltb_checked.add("100")
        # Still needs achievement check
        assert service.needs_enrichment("100") is True

    def test_needs_enrichment_all_checked(self, service: GameDetailService, games: dict) -> None:
        """Returns False when everything is already checked."""
        games["100"].developer = "Valve"
        games["100"].proton_db_rating = "gold"
        games["100"].steam_deck_status = "verified"
        service._hltb_checked.add("100")
        service._achievements_checked.add("100")
        assert service.needs_enrichment("100") is False

    def test_needs_enrichment_has_hltb_data(self, service: GameDetailService, games: dict) -> None:
        """Returns False for HLTB when data is already present."""
        games["100"].developer = "Valve"
        games["100"].proton_db_rating = "gold"
        games["100"].steam_deck_status = "verified"
        games["100"].hltb_main_story = 10.0
        service._achievements_checked.add("100")
        assert service.needs_enrichment("100") is False

    def test_needs_enrichment_has_achievement_data(self, service: GameDetailService, games: dict) -> None:
        """Returns False for achievements when total > 0."""
        games["100"].developer = "Valve"
        games["100"].proton_db_rating = "gold"
        games["100"].steam_deck_status = "verified"
        games["100"].achievement_total = 50
        service._hltb_checked.add("100")
        assert service.needs_enrichment("100") is False

    def test_needs_enrichment_non_game_type(self, service: GameDetailService, games: dict) -> None:
        """Non-game types skip achievement check."""
        games["100"].developer = "Valve"
        games["100"].proton_db_rating = "gold"
        games["100"].steam_deck_status = "verified"
        games["100"].app_type = "tool"
        service._hltb_checked.add("100")
        assert service.needs_enrichment("100") is False

    def test_needs_enrichment_unknown_app_id(self, service: GameDetailService) -> None:
        """Returns False for an unknown app_id."""
        assert service.needs_enrichment("999") is False


# ---------------------------------------------------------------------------
# _fetch_hltb_data()
# ---------------------------------------------------------------------------


class TestFetchHltbData:
    """Tests for on-demand HLTB fetching."""

    def test_skips_if_already_checked(self, service: GameDetailService, games: dict) -> None:
        """Skips fetch if app_id is in _hltb_checked."""
        service._hltb_checked.add("100")
        service._fetch_hltb_data("100")
        assert games["100"].hltb_main_story == 0.0

    def test_skips_if_data_present(self, service: GameDetailService, games: dict) -> None:
        """Skips fetch if HLTB data is already on the game object."""
        games["100"].hltb_main_story = 15.0
        service._fetch_hltb_data("100")
        assert "100" in service._hltb_checked
        assert games["100"].hltb_main_story == 15.0

    def test_loads_from_cache(self, service: GameDetailService, games: dict, cache_dir: Path) -> None:
        """Loads HLTB data from JSON cache if available."""
        cache_file = cache_dir / "store_data" / "100_hltb.json"
        cache_file.write_text(
            json.dumps(
                {
                    "main_story": 12.5,
                    "main_extras": 18.0,
                    "completionist": 25.0,
                }
            )
        )

        service._fetch_hltb_data("100")

        assert games["100"].hltb_main_story == 12.5
        assert games["100"].hltb_main_extras == 18.0
        assert games["100"].hltb_completionist == 25.0
        assert "100" in service._hltb_checked

    def test_loads_no_data_from_cache(self, service: GameDetailService, games: dict, cache_dir: Path) -> None:
        """Cached 'no_data' result does not set HLTB fields."""
        cache_file = cache_dir / "store_data" / "100_hltb.json"
        cache_file.write_text(json.dumps({"no_data": True}))

        service._fetch_hltb_data("100")

        assert games["100"].hltb_main_story == 0.0
        assert "100" in service._hltb_checked

    @patch("src.services.game_detail_service.persist_hltb")
    def test_fetches_from_api(self, mock_persist: MagicMock, service: GameDetailService, games: dict) -> None:
        """Fetches from HLTB API when no cache exists."""
        mock_result = MagicMock()
        mock_result.main_story = 10.0
        mock_result.main_extras = 15.0
        mock_result.completionist = 20.0

        mock_client = MagicMock()
        mock_client.search_game.return_value = mock_result
        service._hltb_client = mock_client

        service._fetch_hltb_data("100")

        mock_client.search_game.assert_called_once_with("Test Game", 100)
        assert games["100"].hltb_main_story == 10.0
        assert games["100"].hltb_main_extras == 15.0
        assert games["100"].hltb_completionist == 20.0
        mock_persist.assert_called_once_with(100, 10.0, 15.0, 20.0)
        assert "100" in service._hltb_checked

    @patch("src.services.game_detail_service.persist_hltb")
    def test_api_no_match(
        self, mock_persist: MagicMock, service: GameDetailService, games: dict, cache_dir: Path
    ) -> None:
        """Caches 'no_data' when HLTB API returns no match."""
        mock_client = MagicMock()
        mock_client.search_game.return_value = None
        service._hltb_client = mock_client

        service._fetch_hltb_data("100")

        assert games["100"].hltb_main_story == 0.0
        mock_persist.assert_not_called()
        # Should have cached no_data
        cache_file = cache_dir / "store_data" / "100_hltb.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert data.get("no_data") is True
        assert "100" in service._hltb_checked

    def test_api_error_handled(self, service: GameDetailService, games: dict) -> None:
        """API errors are caught and app_id is still marked as checked."""
        mock_client = MagicMock()
        mock_client.search_game.side_effect = Exception("Network error")
        service._hltb_client = mock_client

        service._fetch_hltb_data("100")

        assert games["100"].hltb_main_story == 0.0
        assert "100" in service._hltb_checked


# ---------------------------------------------------------------------------
# _fetch_achievement_data()
# ---------------------------------------------------------------------------


class TestFetchAchievementData:
    """Tests for on-demand achievement fetching."""

    def test_skips_if_already_checked(self, service: GameDetailService, games: dict) -> None:
        """Skips fetch if app_id is in _achievements_checked."""
        service._achievements_checked.add("100")
        service._fetch_achievement_data("100")
        assert games["100"].achievement_total == 0

    def test_skips_if_data_present(self, service: GameDetailService, games: dict) -> None:
        """Skips if achievement_total > 0."""
        games["100"].achievement_total = 30
        service._fetch_achievement_data("100")
        assert "100" in service._achievements_checked

    def test_skips_non_game_type(self, service: GameDetailService, games: dict) -> None:
        """Skips non-game types (tool, dlc, etc.)."""
        games["100"].app_type = "tool"
        service._fetch_achievement_data("100")
        assert "100" in service._achievements_checked
        assert games["100"].achievement_total == 0

    def test_loads_from_cache(self, service: GameDetailService, games: dict, cache_dir: Path) -> None:
        """Loads achievement data from JSON cache."""
        cache_file = cache_dir / "store_data" / "100_achievements.json"
        cache_file.write_text(
            json.dumps(
                {
                    "total": 50,
                    "unlocked": 25,
                    "percentage": 50.0,
                    "perfect": False,
                }
            )
        )

        service._fetch_achievement_data("100")

        assert games["100"].achievement_total == 50
        assert games["100"].achievement_unlocked == 25
        assert games["100"].achievement_percentage == 50.0
        assert games["100"].achievement_perfect is False
        assert "100" in service._achievements_checked

    def test_loads_zero_total_from_cache(self, service: GameDetailService, games: dict, cache_dir: Path) -> None:
        """Cached total=0 means game has no achievements."""
        cache_file = cache_dir / "store_data" / "100_achievements.json"
        cache_file.write_text(
            json.dumps(
                {
                    "total": 0,
                    "unlocked": 0,
                    "percentage": 0.0,
                    "perfect": False,
                }
            )
        )

        service._fetch_achievement_data("100")

        assert games["100"].achievement_total == 0
        assert "100" in service._achievements_checked

    @patch("src.services.game_detail_service.persist_achievements")
    @patch("src.services.game_detail_service.persist_achievement_stats")
    def test_fetches_from_api_with_achievements(
        self,
        mock_persist_stats: MagicMock,
        mock_persist_records: MagicMock,
        service: GameDetailService,
        games: dict,
    ) -> None:
        """Fetches achievements from Steam API when no cache exists."""
        mock_schema = {
            "achievements": [
                {"name": "ACH_001", "displayName": "First", "description": "Do it", "hidden": 0},
                {"name": "ACH_002", "displayName": "Second", "description": "Do more", "hidden": 1},
            ]
        }
        mock_player = [
            {"apiname": "ACH_001", "achieved": 1, "unlocktime": 1700000000},
            {"apiname": "ACH_002", "achieved": 0, "unlocktime": 0},
        ]
        mock_global = {"ACH_001": 85.5, "ACH_002": 5.2}

        with (
            patch("src.integrations.steam_web_api.SteamWebAPI") as MockAPI,
            patch("src.config.config") as mock_config,
        ):
            mock_config.STEAM_API_KEY = "test_key"
            mock_config.STEAM_USER_ID = "76561198000000000"

            mock_api_instance = MockAPI.return_value
            mock_api_instance.get_game_schema.return_value = mock_schema
            mock_api_instance.get_player_achievements.return_value = mock_player
            MockAPI.get_global_achievement_percentages.return_value = mock_global

            service._fetch_achievement_data("100")

        assert games["100"].achievement_total == 2
        assert games["100"].achievement_unlocked == 1
        assert games["100"].achievement_percentage == 50.0
        assert games["100"].achievement_perfect is False
        mock_persist_stats.assert_called_once()
        mock_persist_records.assert_called_once()
        assert "100" in service._achievements_checked

    @patch("src.services.game_detail_service.persist_achievement_stats")
    def test_fetches_no_achievements(
        self,
        mock_persist_stats: MagicMock,
        service: GameDetailService,
        games: dict,
        cache_dir: Path,
    ) -> None:
        """Game with no achievements gets total=0 cached."""
        with (
            patch("src.integrations.steam_web_api.SteamWebAPI") as MockAPI,
            patch("src.config.config") as mock_config,
        ):
            mock_config.STEAM_API_KEY = "test_key"
            mock_config.STEAM_USER_ID = "76561198000000000"

            mock_api_instance = MockAPI.return_value
            mock_api_instance.get_game_schema.return_value = {"achievements": []}

            service._fetch_achievement_data("100")

        assert games["100"].achievement_total == 0
        mock_persist_stats.assert_called_once_with(100, 0, 0, 0.0, False)
        cache_file = cache_dir / "store_data" / "100_achievements.json"
        assert cache_file.exists()
        assert "100" in service._achievements_checked

    def test_skips_without_api_key(self, service: GameDetailService, games: dict) -> None:
        """Skips fetch when API key is not configured."""
        with patch("src.config.config") as mock_config:
            mock_config.STEAM_API_KEY = None
            mock_config.STEAM_USER_ID = "76561198000000000"
            service._fetch_achievement_data("100")

        assert games["100"].achievement_total == 0
        assert "100" in service._achievements_checked

    def test_skips_without_steam_id(self, service: GameDetailService, games: dict) -> None:
        """Skips fetch when Steam user ID is not configured."""
        with patch("src.config.config") as mock_config:
            mock_config.STEAM_API_KEY = "test_key"
            mock_config.STEAM_USER_ID = None
            service._fetch_achievement_data("100")

        assert games["100"].achievement_total == 0
        assert "100" in service._achievements_checked

    def test_api_error_handled(self, service: GameDetailService, games: dict) -> None:
        """API errors are caught and app_id is still marked as checked."""
        with (
            patch("src.integrations.steam_web_api.SteamWebAPI") as MockAPI,
            patch("src.config.config") as mock_config,
        ):
            mock_config.STEAM_API_KEY = "test_key"
            mock_config.STEAM_USER_ID = "76561198000000000"
            MockAPI.side_effect = Exception("Connection error")

            service._fetch_achievement_data("100")

        assert games["100"].achievement_total == 0
        assert "100" in service._achievements_checked


# ---------------------------------------------------------------------------
# Apply helper functions (enrichers)
# ---------------------------------------------------------------------------


class TestApplyHelpers:
    """Tests for apply_hltb_data and apply_achievement_data enricher functions."""

    def test_apply_hltb_data(self) -> None:
        """Applies HLTB data to game object."""
        game = Game(app_id="100", name="Test Game")
        data = {"main_story": 8.5, "main_extras": 12.0, "completionist": 20.0}
        apply_hltb_data(game, data)
        assert game.hltb_main_story == 8.5
        assert game.hltb_main_extras == 12.0
        assert game.hltb_completionist == 20.0

    def test_apply_hltb_no_data(self) -> None:
        """Does not modify game when data has no_data flag."""
        game = Game(app_id="100", name="Test Game")
        data = {"no_data": True}
        apply_hltb_data(game, data)
        assert game.hltb_main_story == 0.0

    def test_apply_achievement_data(self) -> None:
        """Applies achievement data to game object."""
        game = Game(app_id="100", name="Test Game")
        data = {"total": 40, "unlocked": 20, "percentage": 50.0, "perfect": False}
        apply_achievement_data(game, data)
        assert game.achievement_total == 40
        assert game.achievement_unlocked == 20
        assert game.achievement_percentage == 50.0
        assert game.achievement_perfect is False

    def test_apply_achievement_perfect(self) -> None:
        """Applies perfect game achievement data."""
        game = Game(app_id="100", name="Test Game")
        data = {"total": 10, "unlocked": 10, "percentage": 100.0, "perfect": True}
        apply_achievement_data(game, data)
        assert game.achievement_total == 10
        assert game.achievement_perfect is True

    def test_enricher_functions_work_standalone(self) -> None:
        """Enricher functions can be called directly without service."""
        game = Game(app_id="999", name="Test")
        apply_hltb_data(game, {"main_story": 5.0})
        assert game.hltb_main_story == 5.0
        apply_achievement_data(game, {"total": 10})
        assert game.achievement_total == 10
