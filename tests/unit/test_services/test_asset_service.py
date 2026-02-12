"""Unit tests for AssetService."""

import pytest
from unittest.mock import Mock, patch
from src.services.asset_service import AssetService


@pytest.fixture
def mock_steam_assets():
    """Mocks SteamAssets static methods."""
    with patch("src.services.asset_service.SteamAssets") as mock_sa:
        yield mock_sa


@pytest.fixture
def mock_steamgrid():
    """Mocks SteamGridDB."""
    with patch("src.services.asset_service.SteamGridDB") as mock_sg:
        yield mock_sg


class TestAssetService:
    """Test suite for AssetService."""

    def test_init_without_steamgrid(self, mock_steamgrid):
        """Test initialization when SteamGridDB fails."""
        mock_steamgrid.side_effect = ValueError("No API key")

        service = AssetService()

        assert service.steamgrid is None

    def test_init_with_steamgrid(self, mock_steamgrid):
        """Test initialization with SteamGridDB."""
        mock_instance = Mock()
        mock_steamgrid.return_value = mock_instance

        service = AssetService()

        assert service.steamgrid is not None

    def test_get_asset_path(self, mock_steam_assets):
        """Test getting asset path."""
        mock_steam_assets.get_asset_path.return_value = "/fake/path/123p.png"

        service = AssetService()
        result = service.get_asset_path("123", "grids")

        assert result == "/fake/path/123p.png"
        assert mock_steam_assets.get_asset_path.call_count == 1  # type: ignore[attr-defined]

    def test_save_custom_image(self, mock_steam_assets):
        """Test saving custom image."""
        mock_steam_assets.save_custom_image.return_value = True

        service = AssetService()
        result = service.save_custom_image("123", "grids", "https://example.com/image.png")

        assert result is True
        assert mock_steam_assets.save_custom_image.call_count == 1  # type: ignore[attr-defined]

    def test_delete_custom_image(self, mock_steam_assets):
        """Test deleting custom image."""
        mock_steam_assets.delete_custom_image.return_value = True

        service = AssetService()
        result = service.delete_custom_image("123", "grids")

        assert result is True
        assert mock_steam_assets.delete_custom_image.call_count == 1  # type: ignore[attr-defined]

    def test_get_steam_grid_path(self, mock_steam_assets):
        """Test getting Steam grid path."""
        from pathlib import Path

        fake_path = Path("/fake/steam/userdata/12345678/config/grid")
        mock_steam_assets.get_steam_grid_path.return_value = fake_path

        service = AssetService()
        result = service.get_steam_grid_path()

        assert result == fake_path
        assert mock_steam_assets.get_steam_grid_path.call_count == 1  # type: ignore[attr-defined]

    def test_fetch_images_from_steamgrid_no_api(self, mock_steamgrid):
        """Test fetching images without SteamGridDB API."""
        mock_steamgrid.side_effect = ValueError("No API key")

        service = AssetService()
        result = service.fetch_images_from_steamgrid("123", "grids")

        assert result == []

    def test_fetch_images_from_steamgrid_success(self, mock_steamgrid):
        """Test successful fetch from SteamGridDB."""
        mock_instance = Mock()
        mock_instance.get_images_by_type.return_value = [
            {"url": "https://example.com/1.png"},
            {"url": "https://example.com/2.png"},
        ]
        mock_steamgrid.return_value = mock_instance

        service = AssetService()
        result = service.fetch_images_from_steamgrid("123", "grids")

        assert len(result) == 2
        assert mock_instance.get_images_by_type.call_count == 1  # type: ignore[attr-defined]

    def test_get_single_images_from_steamgrid_no_api(self, mock_steamgrid):
        """Test getting single images without SteamGridDB API."""
        mock_steamgrid.side_effect = ValueError("No API key")

        service = AssetService()
        result = service.get_single_images_from_steamgrid("123")

        assert result == {}

    def test_get_single_images_from_steamgrid_success(self, mock_steamgrid):
        """Test successful fetch of single images from SteamGridDB."""
        mock_instance = Mock()
        mock_instance.get_images_for_game.return_value = {
            "grids": "https://example.com/grid.png",
            "heroes": "https://example.com/hero.png",
            "logos": "https://example.com/logo.png",
            "icons": "https://example.com/icon.png",
        }
        mock_steamgrid.return_value = mock_instance

        service = AssetService()
        result = service.get_single_images_from_steamgrid("123")

        assert len(result) == 4
        assert "grids" in result
        assert mock_instance.get_images_for_game.call_count == 1  # type: ignore[attr-defined]
