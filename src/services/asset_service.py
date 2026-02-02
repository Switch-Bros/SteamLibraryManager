"""Service for managing game assets (images, icons, logos).

This module provides the AssetService class which handles loading, saving,
and fetching game assets from local storage and external sources like SteamGridDB.
"""

from typing import Optional
from pathlib import Path
from PyQt6.QtGui import QPixmap

from src.integrations.steamgrid_api import SteamGridDB


class AssetService:
    """Service for managing game assets.

    Handles loading images from local cache, saving images to cache,
    and fetching images from external sources like SteamGridDB.

    Attributes:
        cache_dir: Directory for caching game assets.
        steamgrid_api_key: Optional API key for SteamGridDB.
        steamgrid: Optional SteamGridDB instance for fetching assets.
    """

    def __init__(self, cache_dir: str, steamgrid_api_key: Optional[str] = None):
        """Initializes the AssetService.

        Args:
            cache_dir: Directory for caching game assets.
            steamgrid_api_key: Optional API key for SteamGridDB.
        """
        self.cache_dir = Path(cache_dir)
        self.steamgrid_api_key = steamgrid_api_key
        self.steamgrid: Optional[SteamGridDB] = None

        if steamgrid_api_key:
            self.steamgrid = SteamGridDB(steamgrid_api_key)

    def load_image(self, app_id: str, image_type: str = "header") -> Optional[QPixmap]:
        """Loads an image from local cache.

        Args:
            app_id: Steam app ID.
            image_type: Type of image (header, capsule, hero, logo, icon).

        Returns:
            QPixmap if image exists, None otherwise.
        """
        image_path = self.cache_dir / "images" / image_type / f"{app_id}.jpg"

        if not image_path.exists():
            return None

        pixmap = QPixmap(str(image_path))
        return pixmap if not pixmap.isNull() else None

    def save_image(self, app_id: str, pixmap: QPixmap, image_type: str = "header") -> bool:
        """Saves an image to local cache.

        Args:
            app_id: Steam app ID.
            pixmap: QPixmap to save.
            image_type: Type of image (header, capsule, hero, logo, icon).

        Returns:
            True if saved successfully, False otherwise.
        """
        image_dir = self.cache_dir / "images" / image_type
        image_dir.mkdir(parents=True, exist_ok=True)

        image_path = image_dir / f"{app_id}.jpg"
        return pixmap.save(str(image_path), "JPG", quality=95)

    def fetch_from_steamgrid(self, app_id: str, image_type: str = "header") -> Optional[QPixmap]:
        """Fetches an image from SteamGridDB.

        Args:
            app_id: Steam app ID.
            image_type: Type of image (header, capsule, hero, logo, icon).

        Returns:
            QPixmap if fetched successfully, None otherwise.

        Raises:
            RuntimeError: If SteamGridDB is not initialized.
        """
        if not self.steamgrid:
            raise RuntimeError("SteamGridDB not initialized. Provide API key in constructor.")

        # Fetch from SteamGridDB
        image_data = self.steamgrid.get_image(app_id, image_type)

        if not image_data:
            return None

        # Convert to QPixmap
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)

        if pixmap.isNull():
            return None

        # Save to cache
        self.save_image(app_id, pixmap, image_type)

        return pixmap

    def get_image(self, app_id: str, image_type: str = "header", fetch_if_missing: bool = True) -> Optional[QPixmap]:
        """Gets an image from cache or fetches from SteamGridDB if missing.

        Args:
            app_id: Steam app ID.
            image_type: Type of image (header, capsule, hero, logo, icon).
            fetch_if_missing: Whether to fetch from SteamGridDB if not in cache.

        Returns:
            QPixmap if found or fetched, None otherwise.
        """
        # Try cache first
        pixmap = self.load_image(app_id, image_type)

        if pixmap:
            return pixmap

        # Fetch from SteamGridDB if enabled
        if fetch_if_missing and self.steamgrid:
            try:
                return self.fetch_from_steamgrid(app_id, image_type)
            except Exception as e:
                print(f"[WARN] Failed to fetch image from SteamGridDB: {e}")

        return None

    def clear_cache(self, app_id: Optional[str] = None, image_type: Optional[str] = None) -> int:
        """Clears image cache.

        Args:
            app_id: Optional app ID to clear specific game images.
            image_type: Optional image type to clear specific type.

        Returns:
            Number of files deleted.
        """
        deleted = 0

        if app_id and image_type:
            # Clear specific image
            image_path = self.cache_dir / "images" / image_type / f"{app_id}.jpg"
            if image_path.exists():
                image_path.unlink()
                deleted = 1
        elif app_id:
            # Clear all images for app
            for img_type in ["header", "capsule", "hero", "logo", "icon"]:
                image_path = self.cache_dir / "images" / img_type / f"{app_id}.jpg"
                if image_path.exists():
                    image_path.unlink()
                    deleted += 1
        elif image_type:
            # Clear all images of type
            image_dir = self.cache_dir / "images" / image_type
            if image_dir.exists():
                for image_path in image_dir.glob("*.jpg"):
                    image_path.unlink()
                    deleted += 1
        else:
            # Clear all images
            images_dir = self.cache_dir / "images"
            if images_dir.exists():
                for image_path in images_dir.rglob("*.jpg"):
                    image_path.unlink()
                    deleted += 1

        return deleted
