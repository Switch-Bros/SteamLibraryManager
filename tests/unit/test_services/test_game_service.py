"""Unit tests for GameService."""

import pytest
from unittest.mock import Mock, patch
from src.services.game_service import GameService


@pytest.fixture
def mock_dependencies():
    """Mocks all dependencies for GameService."""
    with (
        patch("src.services.game_service.GameManager") as mock_gm,
        patch("src.services.game_service.LocalConfigHelper") as mock_lcp,
        patch("src.services.game_service.CloudStorageParser") as mock_csp,
        patch("src.services.game_service.AppInfoManager") as mock_aim,
    ):
        yield {
            "GameManager": mock_gm,
            "LocalConfigHelper": mock_lcp,
            "CloudStorageParser": mock_csp,
            "AppInfoManager": mock_aim,
        }


class TestGameService:
    """Test suite for GameService."""

    def test_init(self):
        """Test GameService initialization."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")

        assert service.steam_path == "/fake/steam"
        assert service.api_key == "fake_api_key"
        assert service.cache_dir == "/fake/cache"
        assert service.localconfig_helper is None
        assert service.cloud_storage_parser is None
        assert service.game_manager is None

    def test_initialize_parsers_both_success(self, mock_dependencies):
        """Test successful initialization of both parsers."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")

        # Mock successful load() calls
        mock_vdf_instance = mock_dependencies["LocalConfigHelper"].return_value
        mock_vdf_instance.load.return_value = True

        mock_cloud_instance = mock_dependencies["CloudStorageParser"].return_value
        mock_cloud_instance.load.return_value = True

        vdf_success, cloud_success = service.initialize_parsers("/fake/localconfig.vdf", "12345678")

        assert vdf_success is True
        assert cloud_success is True
        assert service.localconfig_helper is not None
        assert service.cloud_storage_parser is not None

    def test_initialize_parsers_vdf_fails(self, mock_dependencies):
        """Test initialization when VDF parser fails."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")

        # Make VDF parser fail (must be an error the except clause catches)
        mock_dependencies["LocalConfigHelper"].side_effect = OSError("VDF error")

        # Cloud parser succeeds
        mock_cloud_instance = mock_dependencies["CloudStorageParser"].return_value
        mock_cloud_instance.load.return_value = True

        vdf_success, cloud_success = service.initialize_parsers("/fake/localconfig.vdf", "12345678")

        assert vdf_success is False
        assert cloud_success is True

    def test_initialize_parsers_cloud_fails_vdf_succeeds(self, mock_dependencies):
        """Test initialization when Cloud parser fails but VDF succeeds."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")

        # VDF parser succeeds
        mock_vdf_instance = mock_dependencies["LocalConfigHelper"].return_value
        mock_vdf_instance.load.return_value = True

        # Make Cloud parser fail (caught by the broad except Exception clause)
        mock_dependencies["CloudStorageParser"].side_effect = Exception("Cloud error")

        vdf_success, cloud_success = service.initialize_parsers("/fake/localconfig.vdf", "12345678")

        assert vdf_success is True
        assert cloud_success is False

    def test_load_games_success(self, mock_dependencies):
        """Test successful game loading."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()  # Simulate initialized parser

        # Mock successful game loading
        mock_gm_instance = mock_dependencies["GameManager"].return_value
        mock_gm_instance.load_games.return_value = True
        mock_gm_instance.games = {"123": Mock()}

        result = service.load_games("76561197960287930")

        assert result is True
        assert service.game_manager is not None
        assert mock_gm_instance.load_games.call_count == 1  # type: ignore[attr-defined]

    def test_load_games_no_parsers(self, mock_dependencies):
        """Test game loading without initialized parsers."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")

        with pytest.raises(RuntimeError, match="Parsers not initialized"):
            service.load_games("76561197960287930")

    def test_load_games_no_games_found(self, mock_dependencies):
        """Test game loading when no games are found."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()

        # Mock empty games
        mock_gm_instance = mock_dependencies["GameManager"].return_value
        mock_gm_instance.load_games.return_value = True
        mock_gm_instance.games = {}

        result = service.load_games("76561197960287930")

        assert result is False

    def test_merge_with_localconfig(self, mock_dependencies):
        """Test merging with localconfig."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()
        service.game_manager = Mock()

        service.merge_with_localconfig()

        assert service.game_manager.merge_with_localconfig.call_count == 1  # type: ignore[attr-defined]

    def test_merge_with_localconfig_no_game_manager(self, mock_dependencies):
        """Test merging without game_manager."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")

        with pytest.raises(RuntimeError, match="GameManager not initialized"):
            service.merge_with_localconfig()

    def test_apply_metadata(self, mock_dependencies):
        """Test applying metadata."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.game_manager = Mock()

        service.apply_metadata()

        assert service.appinfo_manager is not None
        assert service.game_manager.apply_metadata_overrides.call_count == 1  # type: ignore[attr-defined]

    def test_get_active_parser_cloud_available(self, mock_dependencies):
        """Test getting active parser when cloud storage is available."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.localconfig_helper = Mock()
        service.cloud_storage_parser = Mock()

        parser = service.get_active_parser()

        assert parser == service.cloud_storage_parser

    def test_get_active_parser_only_vdf(self, mock_dependencies):
        """Test getting active parser when only VDF is available returns None."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.localconfig_helper = Mock()

        parser = service.get_active_parser()

        assert parser is None
