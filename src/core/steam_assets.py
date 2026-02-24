# src/core/steam_assets.py

"""
Manages Steam game assets (images) for the library.

This module handles retrieving, saving, and deleting local game assets such as
grids, heroes, logos, and icons. It supports custom images and various formats
including WebP and GIF.

IMPORTANT: Images are now saved directly in Steam's grid folder so they appear
in the Steam client!

ENHANCEMENTS (2026-02-13):
✅ Database integration for artwork metadata
✅ Export/Import for multi-device sync
✅ Hash tracking for deduplication
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from src.config import config
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.core.database import Database

logger = logging.getLogger("steamlibmgr.steam_assets")

__all__ = ["SteamAssets"]


class SteamAssets:
    """
    Static manager class for Steam game assets (images).

    This class provides methods to locate, save, and delete game images. It
    searches for custom images first, then checks Steam's local cache, and
    finally falls back to Steam's CDN URLs.

    ENHANCEMENTS:
    - Save artwork metadata to database
    - Export/Import artwork packages for multi-device sync
    - Track file hashes for deduplication
    """

    # Artwork type mapping (UI name → database name)
    ASSET_TYPE_MAP = {
        "grids": "grid_p",  # Portrait grid
        "heroes": "hero",
        "logos": "logo",
        "icons": "icon",
        "capsules": "grid_h",  # Horizontal grid
    }

    # Filename suffix per asset type (appended to app_id)
    _FILENAME_SUFFIXES: dict[str, str] = {
        "grids": "p",
        "heroes": "_hero",
        "logos": "_logo",
        "icons": "_icon",
        "capsules": "",
    }

    # CDN URL paths per asset type
    _CDN_PATHS: dict[str, str] = {
        "grids": "library_600x900.jpg",
        "heroes": "library_hero.jpg",
        "logos": "logo.png",
        "icons": "icon.jpg",
        "capsules": "header.jpg",
    }

    # Filename suffix keyed by DB type name (for export/import)
    _DB_FILENAME_SUFFIXES: dict[str, str] = {
        "grid_p": "p",
        "grid_h": "",
        "hero": "_hero",
        "logo": "_logo",
        "icon": "_icon",
    }

    @staticmethod
    def get_steam_grid_path() -> Path:
        """
        Returns the Steam grid directory path for the current user.

        Returns:
            Path: Path to Steam's grid directory (userdata/<user_id>/config/grid/)
        """
        if not config.STEAM_PATH:
            raise ValueError("Steam path not configured")

        short_id, _ = config.get_detected_user()
        if not short_id:
            raise ValueError("Steam user not detected")

        grid_dir = config.STEAM_PATH / "userdata" / short_id / "config" / "grid"
        grid_dir.mkdir(parents=True, exist_ok=True)

        return grid_dir

    @staticmethod
    def get_asset_path(app_id: str, asset_type: str) -> str:
        """
        Returns the path to a local asset or a URL as fallback.

        This method searches for assets in the following order:
        1. Local Steam user config/grid directory (where Steam looks!)
        2. Steam CDN URLs (fallback)

        Args:
            app_id (str): The Steam app ID.
            asset_type (str): Type of asset to retrieve. Valid values are:
                             'grids', 'heroes', 'logos', 'icons'.

        Returns:
            str: A local file path if the asset exists locally, or a Steam CDN URL
                as fallback. Returns an empty string if the asset type is invalid.
        """

        short_id, _ = config.get_detected_user()

        # Try to find local image in Steam user config
        if config.STEAM_PATH and short_id:
            grid_dir = config.STEAM_PATH / "userdata" / short_id / "config" / "grid"

            # Determine base filename based on asset type
            suffix = SteamAssets._FILENAME_SUFFIXES.get(asset_type)
            if suffix is not None:
                filename_base = f"{app_id}{suffix}"
                # Check all possible extensions
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    local_path = grid_dir / (filename_base + ext)
                    if local_path.exists():
                        return str(local_path)

        # Fallback to Steam CDN URLs
        cdn_path = SteamAssets._CDN_PATHS.get(asset_type)
        if cdn_path:
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/{cdn_path}"
        return ""

    @staticmethod
    def save_custom_image(
        app_id: str, asset_type: str, url_or_path: str, db: Database | None = None, source: str = "steamgriddb"
    ) -> bool:
        """
        Saves a custom image for a game directly in Steam's grid folder.

        Downloads an image from a URL or copies it from a local path and saves it
        to Steam's grid directory with the correct filename so it appears in the
        Steam client.

        ENHANCED: Now saves metadata to database for multi-device sync!

        Args:
            app_id: Steam app ID.
            asset_type: Type of asset ('grids', 'heroes', 'logos', 'icons', 'capsules').
            url_or_path: Source URL (http/https) or local file path.
            db: Optional Database instance for metadata storage.
            source: Source of artwork ('steamgriddb', 'local', 'custom').

        Returns:
            True if the image was saved successfully, False otherwise.
        """
        try:
            # Get Steam grid directory
            grid_dir = SteamAssets.get_steam_grid_path()

            # Determine correct filename for Steam
            suffix = SteamAssets._FILENAME_SUFFIXES.get(asset_type)
            if suffix is None:
                logger.info(t("logs.assets.unknown_type", type=asset_type))
                return False
            filename = f"{app_id}{suffix}.png"

            target_file = grid_dir / filename

            # Download URL
            if str(url_or_path).startswith("http"):
                headers = {"User-Agent": "SteamLibraryManager/1.0"}
                response = requests.get(url_or_path, headers=headers, timeout=10)
                if response.status_code == 200:
                    with open(target_file, "wb") as f:
                        f.write(response.content)
                    logger.info(t("logs.steamgrid.saved", type=asset_type, app_id=app_id))
                    logger.info(t("logs.assets.saved_to", path=target_file))

                    # Save metadata to database
                    if db:
                        SteamAssets._save_artwork_metadata(
                            db, app_id, asset_type, target_file, source, str(url_or_path)
                        )

                    return True

            # Copy local file
            elif os.path.exists(url_or_path):
                shutil.copy2(url_or_path, target_file)
                logger.info(t("logs.steamgrid.saved", type=asset_type, app_id=app_id))
                logger.info(t("logs.assets.saved_to", path=target_file))

                # Save metadata to database
                if db:
                    SteamAssets._save_artwork_metadata(db, app_id, asset_type, target_file, source, None)

                return True

        except (OSError, requests.RequestException, ValueError) as e:
            logger.error(t("logs.steamgrid.save_error", error=e))
            return False

        return False

    @staticmethod
    def _save_artwork_metadata(
        db: Database, app_id: str, asset_type: str, file_path: Path, source: str, source_url: str | None
    ) -> None:
        """Save artwork metadata to database."""
        try:
            # Calculate file hash
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            # Get file size
            file_size = file_path.stat().st_size

            # Get image dimensions (optional, requires PIL)
            width, height = 0, 0
            try:
                from PIL import Image

                with Image.open(file_path) as img:
                    width, height = img.size
            except ImportError:
                pass  # PIL not available

            # Map asset_type to database name
            db_asset_type = SteamAssets.ASSET_TYPE_MAP.get(asset_type, asset_type)

            # Save to database
            db.conn.execute(
                """
                INSERT OR REPLACE INTO custom_artwork
                (app_id, artwork_type, source, source_url, file_hash,
                 file_size, width, height, set_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (int(app_id), db_asset_type, source, source_url, file_hash, file_size, width, height, int(time.time())),
            )
            db.commit()
            logger.debug(f"Saved artwork metadata: {app_id} / {db_asset_type}")

        except Exception as e:
            logger.warning(f"Could not save artwork metadata: {e}")

    @staticmethod
    def delete_custom_image(app_id: str, asset_type: str, db: Database | None = None) -> bool:
        """
        Deletes a custom image for a game from Steam's grid folder.

        This method removes the image file from Steam's grid directory. If the
        file doesn't exist, it returns True (idempotent behavior).

        ENHANCED: Also removes metadata from database!

        Args:
            app_id: Steam app ID.
            asset_type: Type of asset to delete ('grids', 'heroes', 'logos', 'icons').
            db: Optional Database instance.

        Returns:
            True if the image was deleted or didn't exist, False if an error occurred.
        """
        try:
            # Get Steam grid directory
            grid_dir = SteamAssets.get_steam_grid_path()

            # Determine correct filename
            suffix = SteamAssets._FILENAME_SUFFIXES.get(asset_type)
            if suffix is None:
                return False
            filename = f"{app_id}{suffix}.png"

            target_file = grid_dir / filename

            if target_file.exists():
                os.remove(target_file)
                logger.info(t("logs.steamgrid.deleted", path=target_file.name))

            # Remove from database
            if db:
                db_asset_type = SteamAssets.ASSET_TYPE_MAP.get(asset_type, asset_type)
                db.conn.execute(
                    "DELETE FROM custom_artwork WHERE app_id = ? AND artwork_type = ?", (int(app_id), db_asset_type)
                )
                db.commit()

            return True

        except (OSError, ValueError) as e:
            logger.error(t("logs.steamgrid.delete_error", error=e))
            return False

    @staticmethod
    def export_artwork_package(db: Database, export_dir: Path) -> dict[str, int]:
        """
        Export all custom artwork to a package for multi-device sync.

        Creates:
        - artwork/ folder with all custom images
        - artwork_manifest.json with metadata

        Args:
            db: Database instance.
            export_dir: Directory to export to.

        Returns:
            Statistics dict with counts per artwork type.
        """
        artwork_dir = export_dir / "artwork"
        artwork_dir.mkdir(parents=True, exist_ok=True)

        grid_dir = SteamAssets.get_steam_grid_path()

        cursor = db.conn.execute("SELECT * FROM custom_artwork ORDER BY app_id, artwork_type")

        manifest = {}
        stats = {"grid_p": 0, "grid_h": 0, "hero": 0, "logo": 0, "icon": 0}

        for row in cursor.fetchall():
            app_id = row["app_id"]
            artwork_type = row["artwork_type"]
            file_hash = row["file_hash"]

            # Determine source filename
            db_suffix = SteamAssets._DB_FILENAME_SUFFIXES.get(artwork_type)
            if db_suffix is None:
                continue
            source_file = grid_dir / f"{app_id}{db_suffix}.png"

            if not source_file.exists():
                logger.warning(f"Missing artwork file: {source_file}")
                continue

            # Copy to export folder
            dest_filename = f"{app_id}_{artwork_type}_{file_hash[:8]}.png"
            dest_file = artwork_dir / dest_filename
            shutil.copy2(source_file, dest_file)

            # Add to manifest
            manifest[f"{app_id}_{artwork_type}"] = {
                "app_id": app_id,
                "artwork_type": artwork_type,
                "filename": dest_filename,
                "hash": file_hash,
                "source": row["source"],
                "source_url": row["source_url"],
                "width": row["width"],
                "height": row["height"],
                "set_at": row["set_at"],
            }

            stats[artwork_type] += 1

        # Save manifest
        with open(export_dir / "artwork_manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Exported {len(manifest)} custom artworks")
        return stats

    @staticmethod
    def import_artwork_package(db: Database, import_dir: Path) -> dict[str, int]:
        """
        Import artwork package from another device.

        Args:
            db: Database instance.
            import_dir: Directory with artwork/ and manifest.

        Returns:
            Statistics dict with counts per artwork type.
        """
        manifest_file = import_dir / "artwork_manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_file}")

        artwork_dir = import_dir / "artwork"
        if not artwork_dir.exists():
            raise FileNotFoundError(f"Artwork folder not found: {artwork_dir}")

        # Load manifest
        with open(manifest_file) as f:
            manifest = json.load(f)

        grid_dir = SteamAssets.get_steam_grid_path()
        stats = {"grid_p": 0, "grid_h": 0, "hero": 0, "logo": 0, "icon": 0}

        for key, info in manifest.items():
            app_id = info["app_id"]
            artwork_type = info["artwork_type"]
            source_file = artwork_dir / info["filename"]

            if not source_file.exists():
                logger.warning(f"Missing file: {source_file}")
                continue

            # Determine destination filename
            db_suffix = SteamAssets._DB_FILENAME_SUFFIXES.get(artwork_type)
            if db_suffix is None:
                continue
            dest_file = grid_dir / f"{app_id}{db_suffix}.png"

            # Copy file
            shutil.copy2(source_file, dest_file)

            # Update database
            db.conn.execute(
                """
                INSERT OR REPLACE INTO custom_artwork
                (app_id, artwork_type, source, source_url, file_hash,
                 file_size, width, height, set_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    app_id,
                    artwork_type,
                    info["source"],
                    info["source_url"],
                    info["hash"],
                    dest_file.stat().st_size,
                    info["width"],
                    info["height"],
                    info["set_at"],
                ),
            )

            stats[artwork_type] += 1

        db.commit()
        logger.info(f"Imported {len(manifest)} custom artworks")
        return stats
