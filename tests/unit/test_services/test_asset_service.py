"""Unit tests for AssetService."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from PyQt6.QtGui import QPixmap
from src.services.asset_service import AssetService


@pytest.fixture
def tmp_cache_dir(tmp_path):
    """Creates a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def mock_steamgrid():
    """Creates a mock SteamGridDB instance."""
    with patch('src.services.asset_service.SteamGridDB') as mock_sg:
        yield mock_sg


class TestAssetService:
    """Test suite for AssetService."""

    def test_init_without_steamgrid(self, tmp_cache_dir):
        """Test initialization without SteamGridDB API key."""
        service = AssetService(str(tmp_cache_dir))

        assert service.cache_dir == tmp_cache_dir
        assert service.steamgrid_api_key is None
        assert service.steamgrid is None

    def test_init_with_steamgrid(self, tmp_cache_dir, mock_steamgrid):
        """Test initialization with SteamGridDB API key."""
        service = AssetService(str(tmp_cache_dir), "fake_api_key")

        assert service.steamgrid_api_key == "fake_api_key"
        assert service.steamgrid is not None
        mock_steamgrid.assert_called_once_with("fake_api_key")  # type: ignore[attr-defined]

    def test_load_image_exists(self, tmp_cache_dir):
        """Test loading an existing image."""
        service = AssetService(str(tmp_cache_dir))

        # Create a fake image file
        image_dir = tmp_cache_dir / "images" / "header"
        image_dir.mkdir(parents=True)
        image_path = image_dir / "123.jpg"

        # Create a minimal valid JPEG
        with open(image_path, 'wb') as f:
            # Minimal JPEG header
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')

        with patch('src.services.asset_service.QPixmap') as mock_pixmap:
            mock_instance = Mock()
            mock_instance.isNull.return_value = False
            mock_pixmap.return_value = mock_instance

            result = service.load_image("123", "header")

            assert result is not None
            mock_pixmap.assert_called_once()  # type: ignore[attr-defined]

    def test_load_image_not_exists(self, tmp_cache_dir):
        """Test loading a non-existent image."""
        service = AssetService(str(tmp_cache_dir))

        result = service.load_image("999", "header")

        assert result is None

    def test_save_image(self, tmp_cache_dir):
        """Test saving an image."""
        service = AssetService(str(tmp_cache_dir))

        mock_pixmap = Mock(spec=QPixmap)
        mock_pixmap.save.return_value = True

        result = service.save_image("123", mock_pixmap, "header")

        assert result is True
        mock_pixmap.save.assert_called_once()  # type: ignore[attr-defined]

        # Check directory was created
        assert (tmp_cache_dir / "images" / "header").exists()

    def test_fetch_from_steamgrid_no_api_key(self, tmp_cache_dir):
        """Test fetching from SteamGridDB without API key."""
        service = AssetService(str(tmp_cache_dir))

        with pytest.raises(RuntimeError, match="SteamGridDB not initialized"):
            service.fetch_from_steamgrid("123", "header")

    def test_fetch_from_steamgrid_success(self, tmp_cache_dir, mock_steamgrid):
        """Test successful fetch from SteamGridDB."""
        service = AssetService(str(tmp_cache_dir), "fake_api_key")

        # Mock SteamGridDB response
        fake_image_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'
        service.steamgrid.get_image.return_value = fake_image_data

        with patch('src.services.asset_service.QPixmap') as mock_pixmap_class:
            mock_pixmap = Mock()
            mock_pixmap.isNull.return_value = False
            mock_pixmap.save.return_value = True
            mock_pixmap_class.return_value = mock_pixmap

            result = service.fetch_from_steamgrid("123", "header")

            assert result is not None
            service.steamgrid.get_image.assert_called_once_with("123", "header")  # type: ignore[attr-defined]

    def test_get_image_from_cache(self, tmp_cache_dir):
        """Test getting image from cache."""
        service = AssetService(str(tmp_cache_dir))

        # Create a fake image
        image_dir = tmp_cache_dir / "images" / "header"
        image_dir.mkdir(parents=True)
        (image_dir / "123.jpg").write_bytes(
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')

        with patch('src.services.asset_service.QPixmap') as mock_pixmap:
            mock_instance = Mock()
            mock_instance.isNull.return_value = False
            mock_pixmap.return_value = mock_instance

            result = service.get_image("123", "header", fetch_if_missing=False)

            assert result is not None

    def test_clear_cache_specific_image(self, tmp_cache_dir):
        """Test clearing specific image from cache."""
        service = AssetService(str(tmp_cache_dir))

        # Create fake images
        image_dir = tmp_cache_dir / "images" / "header"
        image_dir.mkdir(parents=True)
        (image_dir / "123.jpg").write_text("fake")
        (image_dir / "456.jpg").write_text("fake")

        deleted = service.clear_cache(app_id="123", image_type="header")

        assert deleted == 1
        assert not (image_dir / "123.jpg").exists()
        assert (image_dir / "456.jpg").exists()

    def test_clear_cache_all_images(self, tmp_cache_dir):
        """Test clearing all images from cache."""
        service = AssetService(str(tmp_cache_dir))

        # Create fake images
        for img_type in ["header", "capsule"]:
            image_dir = tmp_cache_dir / "images" / img_type
            image_dir.mkdir(parents=True)
            (image_dir / "123.jpg").write_text("fake")
            (image_dir / "456.jpg").write_text("fake")

        deleted = service.clear_cache()

        assert deleted == 4
