#
# steam_library_manager/core/steam_assets.py
# Manage Steam game artwork - local grid images and CDN fallbacks
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

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

from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

if TYPE_CHECKING:
    from steam_library_manager.core.database import Database

logger = logging.getLogger("steamlibmgr.steam_assets")

__all__ = ["SteamAssets"]


class SteamAssets:
    """Static manager for Steam game artwork (grid images, heroes, logos, icons)."""

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
        """Return the Steam grid directory for the current user."""
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
        """Return local asset path or CDN URL fallback. Empty string if invalid type."""

        short_id, _ = config.get_detected_user()

        if config.STEAM_PATH and short_id:
            grid_dir = config.STEAM_PATH / "userdata" / short_id / "config" / "grid"

            suffix = SteamAssets._FILENAME_SUFFIXES.get(asset_type)
            if suffix is not None:
                filename_base = f"{app_id}{suffix}"
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    local_path = grid_dir / (filename_base + ext)
                    if local_path.exists():
                        return str(local_path)

        cdn_path = SteamAssets._CDN_PATHS.get(asset_type)
        if cdn_path:
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/{cdn_path}"
        return ""

    @staticmethod
    def save_custom_image(
        app_id: str, asset_type: str, url_or_path: str, db: Database | None = None, source: str = "steamgriddb"
    ) -> bool:
        """Download or copy a custom image into Steam's grid folder."""
        try:
            grid_dir = SteamAssets.get_steam_grid_path()
            suffix = SteamAssets._FILENAME_SUFFIXES.get(asset_type)
            if suffix is None:
                logger.info(t("logs.assets.unknown_type", type=asset_type))
                return False
            filename = f"{app_id}{suffix}.png"

            target_file = grid_dir / filename

            if str(url_or_path).startswith("http"):
                headers = {"User-Agent": "SteamLibraryManager/1.0"}
                response = requests.get(url_or_path, headers=headers, timeout=HTTP_TIMEOUT)
                if response.status_code == 200:
                    with open(target_file, "wb") as f:
                        f.write(response.content)
                    logger.info(t("logs.steamgrid.saved", type=asset_type, app_id=app_id))
                    logger.info(t("logs.assets.saved_to", path=target_file))

                    if db:
                        SteamAssets._save_artwork_metadata(
                            db, app_id, asset_type, target_file, source, str(url_or_path)
                        )

                    return True

            elif os.path.exists(url_or_path):
                shutil.copy2(url_or_path, target_file)
                logger.info(t("logs.steamgrid.saved", type=asset_type, app_id=app_id))
                logger.info(t("logs.assets.saved_to", path=target_file))

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
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            file_size = file_path.stat().st_size
            width, height = 0, 0
            try:
                from PIL import Image

                with Image.open(file_path) as img:
                    width, height = img.size
            except ImportError:
                pass

            db_asset_type = SteamAssets.ASSET_TYPE_MAP.get(asset_type, asset_type)
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
        """Remove a custom image from Steam's grid folder. Idempotent."""
        try:
            grid_dir = SteamAssets.get_steam_grid_path()
            suffix = SteamAssets._FILENAME_SUFFIXES.get(asset_type)
            if suffix is None:
                return False
            filename = f"{app_id}{suffix}.png"

            target_file = grid_dir / filename

            if target_file.exists():
                os.remove(target_file)
                logger.info(t("logs.steamgrid.deleted", path=target_file.name))

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
        """Export all custom artwork to a transferable package with manifest."""
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

            db_suffix = SteamAssets._DB_FILENAME_SUFFIXES.get(artwork_type)
            if db_suffix is None:
                continue
            source_file = grid_dir / f"{app_id}{db_suffix}.png"

            if not source_file.exists():
                logger.warning(f"Missing artwork file: {source_file}")
                continue

            dest_filename = f"{app_id}_{artwork_type}_{file_hash[:8]}.png"
            dest_file = artwork_dir / dest_filename
            shutil.copy2(source_file, dest_file)

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

        with open(export_dir / "artwork_manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Exported {len(manifest)} custom artworks")
        return stats

    @staticmethod
    def import_artwork_package(db: Database, import_dir: Path) -> dict[str, int]:
        """Import an artwork package exported from another device."""
        manifest_file = import_dir / "artwork_manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_file}")

        artwork_dir = import_dir / "artwork"
        if not artwork_dir.exists():
            raise FileNotFoundError(f"Artwork folder not found: {artwork_dir}")

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

            db_suffix = SteamAssets._DB_FILENAME_SUFFIXES.get(artwork_type)
            if db_suffix is None:
                continue
            dest_file = grid_dir / f"{app_id}{db_suffix}.png"

            shutil.copy2(source_file, dest_file)
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
