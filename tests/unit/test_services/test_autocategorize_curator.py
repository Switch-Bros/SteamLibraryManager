"""Unit tests for AutoCategorizeService.categorize_by_curator."""

from unittest.mock import Mock, patch, MagicMock

import pytest

from src.core.game import Game
from src.services.autocategorize_service import AutoCategorizeService
from src.services.curator_client import CuratorRecommendation


class TestCategorizeByCurator:
    """Tests for curator-based categorization."""

    @pytest.fixture
    def mock_game_manager(self) -> Mock:
        """Create a mock GameManager."""
        return Mock()

    @pytest.fixture
    def mock_category_service(self) -> Mock:
        """Create a mock CategoryService."""
        service = Mock()
        service.add_app_to_category = Mock()
        return service

    @pytest.fixture
    def service(self, mock_game_manager: Mock, mock_category_service: Mock) -> AutoCategorizeService:
        """Create AutoCategorizeService instance."""
        return AutoCategorizeService(mock_game_manager, mock_category_service)

    @pytest.fixture
    def games(self) -> list[Game]:
        """Create a list of test games."""
        g1 = Game(app_id="440", name="Team Fortress 2")
        g1.categories = []
        g2 = Game(app_id="730", name="Counter-Strike 2")
        g2.categories = []
        g3 = Game(app_id="570", name="Dota 2")
        g3.categories = []
        return [g1, g2, g3]

    @patch("src.services.autocategorize_service.CuratorClient")
    def test_categorize_by_curator_success(
        self, mock_client_cls: MagicMock, service: AutoCategorizeService, games: list[Game]
    ) -> None:
        """Test successful curator categorization with matching games."""
        mock_client = Mock()
        mock_client.fetch_recommendations.return_value = {
            440: CuratorRecommendation.RECOMMENDED,
            730: CuratorRecommendation.NOT_RECOMMENDED,
        }
        mock_client_cls.return_value = mock_client

        count = service.categorize_by_curator(games, curator_url="https://store.steampowered.com/curator/123/")

        # 2 games matched (440 and 730), not 570
        assert count == 2
        mock_client.fetch_recommendations.assert_called_once()

    @patch("src.services.autocategorize_service.CuratorClient")
    def test_categorize_by_curator_no_matches(
        self, mock_client_cls: MagicMock, service: AutoCategorizeService, games: list[Game]
    ) -> None:
        """Test curator categorization when no games match."""
        mock_client = Mock()
        mock_client.fetch_recommendations.return_value = {
            999: CuratorRecommendation.RECOMMENDED,
        }
        mock_client_cls.return_value = mock_client

        count = service.categorize_by_curator(games, curator_url="https://store.steampowered.com/curator/123/")

        assert count == 0

    @patch("src.services.autocategorize_service.CuratorClient")
    def test_categorize_by_curator_filter_types(
        self, mock_client_cls: MagicMock, service: AutoCategorizeService, games: list[Game]
    ) -> None:
        """Test curator categorization with type filtering."""
        mock_client = Mock()
        mock_client.fetch_recommendations.return_value = {
            440: CuratorRecommendation.RECOMMENDED,
            730: CuratorRecommendation.NOT_RECOMMENDED,
            570: CuratorRecommendation.INFORMATIONAL,
        }
        mock_client_cls.return_value = mock_client

        # Only include RECOMMENDED
        count = service.categorize_by_curator(
            games,
            curator_url="https://store.steampowered.com/curator/123/",
            included_types={CuratorRecommendation.RECOMMENDED},
        )

        assert count == 1

    @patch("src.services.autocategorize_service.CuratorClient")
    def test_categorize_by_curator_with_progress_callback(
        self, mock_client_cls: MagicMock, service: AutoCategorizeService, games: list[Game]
    ) -> None:
        """Test that progress callback is invoked for each game."""
        mock_client = Mock()
        mock_client.fetch_recommendations.return_value = {}
        mock_client_cls.return_value = mock_client

        callback = Mock()
        service.categorize_by_curator(
            games,
            curator_url="https://store.steampowered.com/curator/123/",
            progress_callback=callback,
        )

        assert callback.call_count == len(games)

    @patch("src.services.autocategorize_service.CuratorClient")
    def test_categorize_by_curator_empty_games_list(
        self, mock_client_cls: MagicMock, service: AutoCategorizeService
    ) -> None:
        """Test curator categorization with empty game list."""
        mock_client = Mock()
        mock_client.fetch_recommendations.return_value = {440: CuratorRecommendation.RECOMMENDED}
        mock_client_cls.return_value = mock_client

        count = service.categorize_by_curator([], curator_url="https://store.steampowered.com/curator/123/")

        assert count == 0

    @patch("src.services.autocategorize_service.CuratorClient")
    def test_categorize_by_curator_invalid_url_raises(
        self, mock_client_cls: MagicMock, service: AutoCategorizeService, games: list[Game]
    ) -> None:
        """Test that invalid curator URL raises ValueError."""
        mock_client = Mock()
        mock_client.fetch_recommendations.side_effect = ValueError("Invalid curator URL")
        mock_client_cls.return_value = mock_client

        with pytest.raises(ValueError, match="Invalid curator URL"):
            service.categorize_by_curator(games, curator_url="bad-url")
