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
        patch("src.services.game_service.PackageInfoParser") as mock_pip,
        patch("src.services.game_service.LicenseCacheParser") as mock_lcp_parser,
        patch("src.config.config") as mock_cfg,
    ):
        # PackageInfoParser().get_all_app_ids() returns empty set by default
        mock_pip.return_value.get_all_app_ids.return_value = set()
        mock_pip.return_value.get_app_ids_for_packages.return_value = set()
        # LicenseCacheParser defaults: no packages found (fallback to get_all_app_ids)
        mock_lcp_parser.return_value.get_owned_package_ids.return_value = set()
        # Config: no detected user by default (fallback path)
        mock_cfg.get_detected_user.return_value = (None, None)
        yield {
            "GameManager": mock_gm,
            "LocalConfigHelper": mock_lcp,
            "CloudStorageParser": mock_csp,
            "AppInfoManager": mock_aim,
            "PackageInfoParser": mock_pip,
            "LicenseCacheParser": mock_lcp_parser,
            "config": mock_cfg,
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
        service.game_manager.discover_missing_games.return_value = 0

        service.apply_metadata()

        assert service.appinfo_manager is not None
        assert service.game_manager.apply_metadata_overrides.call_count == 1  # type: ignore[attr-defined]

    def test_load_and_prepare_success(self, mock_dependencies):
        """Test full pipeline: load + merge + discover + apply metadata."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()

        mock_gm = mock_dependencies["GameManager"].return_value
        mock_gm.load_games.return_value = True
        mock_gm.games = {"123": Mock()}
        mock_gm.discover_missing_games.return_value = 0

        result = service.load_and_prepare("76561197960287930")

        assert result is True
        mock_gm.merge_with_localconfig.assert_called_once_with(service.cloud_storage_parser)
        mock_gm.discover_missing_games.assert_called_once()
        mock_gm.apply_metadata_overrides.assert_called_once()

    def test_load_and_prepare_load_fails_skips_rest(self, mock_dependencies):
        """Test that merge/metadata are skipped when load_games fails."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()

        mock_gm = mock_dependencies["GameManager"].return_value
        mock_gm.load_games.return_value = False
        mock_gm.games = {}

        result = service.load_and_prepare("76561197960287930")

        assert result is False
        mock_gm.merge_with_localconfig.assert_not_called()
        mock_gm.apply_metadata_overrides.assert_not_called()

    def test_load_and_prepare_discovers_and_remerges(self, mock_dependencies):
        """Test that discovered games trigger a second merge."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()

        mock_gm = mock_dependencies["GameManager"].return_value
        mock_gm.load_games.return_value = True
        mock_gm.games = {"123": Mock()}
        mock_gm.discover_missing_games.return_value = 5  # 5 new games discovered

        result = service.load_and_prepare("76561197960287930")

        assert result is True
        # merge_with_localconfig called twice: initial + re-merge for discovered
        assert mock_gm.merge_with_localconfig.call_count == 2

    def test_load_and_prepare_progress_callbacks(self, mock_dependencies):
        """Test that progress callback is called for each pipeline step."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()

        mock_gm = mock_dependencies["GameManager"].return_value
        mock_gm.load_games.return_value = True
        mock_gm.games = {"123": Mock()}
        mock_gm.discover_missing_games.return_value = 0

        callback = Mock()
        service.load_and_prepare("76561197960287930", callback)

        # Callback is called for: merge, metadata, packages, discover, overrides
        # (load_games also calls it internally, but that's forwarded)
        step_names = [call.args[0] for call in callback.call_args_list]
        assert len(step_names) >= 4  # At least our 4 explicit steps

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

    def test_load_and_prepare_uses_db_for_discovery(self, mock_dependencies):
        """Test that load_and_prepare uses DB lookup instead of binary VDF."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()

        mock_gm = mock_dependencies["GameManager"].return_value
        mock_gm.load_games.return_value = True
        mock_gm.games = {"123": Mock()}
        mock_gm.discover_missing_games.return_value = 0

        # Mock _init_database to return a mock DB (avoids filesystem access)
        mock_db = Mock()
        mock_db.get_game_count.return_value = 100
        mock_db.get_app_type_lookup.return_value = {"456": ("game", "Test")}

        with patch.object(service, "_init_database", return_value=mock_db):
            result = service.load_and_prepare("76561197960287930")

        assert result is True
        # DB lookup should be used
        mock_db.get_app_type_lookup.assert_called_once()
        # discover_missing_games should receive db_type_lookup kwarg
        call_kwargs = mock_gm.discover_missing_games.call_args
        assert call_kwargs.kwargs.get("db_type_lookup") is not None
        # AppInfoManager should NOT have load_appinfo called (binary skip)
        mock_aim_instance = mock_dependencies["AppInfoManager"].return_value
        mock_aim_instance.load_appinfo.assert_not_called()

    def test_load_and_prepare_applies_custom_overrides_only(self, mock_dependencies):
        """Test that load_and_prepare uses apply_custom_overrides (not full binary)."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()

        mock_gm = mock_dependencies["GameManager"].return_value
        mock_gm.load_games.return_value = True
        mock_gm.games = {"123": Mock()}
        mock_gm.discover_missing_games.return_value = 0

        # Mock _init_database to return a mock DB
        mock_db = Mock()
        mock_db.get_game_count.return_value = 100
        mock_db.get_app_type_lookup.return_value = {}

        with patch.object(service, "_init_database", return_value=mock_db):
            result = service.load_and_prepare("76561197960287930")

        assert result is True
        # apply_custom_overrides should be called (not apply_metadata_overrides)
        mock_gm.apply_custom_overrides.assert_called_once()
        mock_gm.apply_metadata_overrides.assert_not_called()

    def test_load_and_prepare_uses_licensecache(self, mock_dependencies):
        """Test that licensecache is used when Steam32 ID is available."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()

        mock_gm = mock_dependencies["GameManager"].return_value
        mock_gm.load_games.return_value = True
        mock_gm.games = {"123": Mock()}
        mock_gm.discover_missing_games.return_value = 0

        # Configure config to return a valid Steam32 ID
        mock_dependencies["config"].get_detected_user.return_value = ("43925226", "76561198004190954")

        # LicenseCacheParser returns owned packages
        mock_lcp = mock_dependencies["LicenseCacheParser"]
        mock_lcp.return_value.get_owned_package_ids.return_value = {100, 200, 300}

        # PackageInfoParser filtered method returns app IDs
        mock_pip = mock_dependencies["PackageInfoParser"]
        mock_pip.return_value.get_app_ids_for_packages.return_value = {"1000", "2000"}

        result = service.load_and_prepare("76561198004190954")

        assert result is True
        # get_app_ids_for_packages should be called with owned packages
        mock_pip.return_value.get_app_ids_for_packages.assert_called_once_with({100, 200, 300})
        # get_all_app_ids should NOT be called (licensecache path used)
        mock_pip.return_value.get_all_app_ids.assert_not_called()

    def test_load_and_prepare_fallback_without_licensecache(self, mock_dependencies):
        """Test fallback to get_all_app_ids when no Steam32 ID available."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()

        mock_gm = mock_dependencies["GameManager"].return_value
        mock_gm.load_games.return_value = True
        mock_gm.games = {"123": Mock()}
        mock_gm.discover_missing_games.return_value = 0

        # No detected user → fallback
        mock_dependencies["config"].get_detected_user.return_value = (None, None)

        mock_pip = mock_dependencies["PackageInfoParser"]

        result = service.load_and_prepare("76561197960287930")

        assert result is True
        # Fallback: get_all_app_ids should be called
        mock_pip.return_value.get_all_app_ids.assert_called_once()
        # Filtered method should NOT be called
        mock_pip.return_value.get_app_ids_for_packages.assert_not_called()

    def test_load_and_prepare_profile_scraper_disabled(self, mock_dependencies):
        """Verify _refresh_from_profile is NOT called in pipeline."""
        service = GameService("/fake/steam", "fake_api_key", "/fake/cache")
        service.cloud_storage_parser = Mock()

        mock_gm = mock_dependencies["GameManager"].return_value
        mock_gm.load_games.return_value = True
        mock_gm.games = {"123": Mock()}
        mock_gm.discover_missing_games.return_value = 0

        with patch.object(service, "_refresh_from_profile") as mock_profile:
            service.load_and_prepare("76561197960287930")
            mock_profile.assert_not_called()
