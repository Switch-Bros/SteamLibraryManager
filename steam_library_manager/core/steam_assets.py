#
# steam_library_manager/core/steam_assets.py
# Steam game artwork: locate, save, delete, export/import
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time

import requests

from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

logger = logging.getLogger("steamlibmgr.steam_assets")

__all__ = ["SteamAssets"]


class SteamAssets:
    """Static manager for Steam game artwork.

    Searches custom images first, then local cache,
    then falls back to CDN. Also handles DB metadata
    and export/import for multi-device sync.
    """

    # UI name -> DB name
    ASSET_TYPE_MAP = {
        "grids": "grid_p",
        "heroes": "hero",
        "logos": "logo",
        "icons": "icon",
        "capsules": "grid_h",
    }

    # filename suffix per type
    _SUFFIXES = {
        "grids": "p",
        "heroes": "_hero",
        "logos": "_logo",
        "icons": "_icon",
        "capsules": "",
    }

    # CDN paths per type (first match wins)
    _CDN = {
        "grids": ["library_600x900.jpg", "library_600x900_2x.jpg", "header.jpg"],
        "heroes": ["library_hero.jpg", "header.jpg"],
        "logos": ["logo.png"],
        "icons": ["icon.jpg"],
        "capsules": ["header.jpg"],
    }

    # DB type -> suffix (for export/import)
    _DB_SUFFIXES = {
        "grid_p": "p",
        "grid_h": "",
        "hero": "_hero",
        "logo": "_logo",
        "icon": "_icon",
    }

    @staticmethod
    def get_steam_grid_path():
        # grid dir for current user
        if not config.STEAM_PATH:
            raise ValueError("Steam path not configured")

        sid, _ = config.get_detected_user()
        if not sid:
            raise ValueError("Steam user not detected")

        gdir = config.STEAM_PATH / "userdata" / sid / "config" / "grid"
        gdir.mkdir(parents=True, exist_ok=True)
        return gdir

    @staticmethod
    def get_asset_path(app_id, asset_type):
        # local path or CDN URL fallback
        sid, _ = config.get_detected_user()

        if config.STEAM_PATH and sid:
            gdir = config.STEAM_PATH / "userdata" / sid / "config" / "grid"

            sfx = SteamAssets._SUFFIXES.get(asset_type)
            if sfx is not None:
                base = "%s%s" % (app_id, sfx)
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    lp = gdir / (base + ext)
                    if lp.exists():
                        return str(lp)

        # CDN fallback
        cdn = SteamAssets._CDN.get(asset_type, [])
        if cdn:
            return "https://cdn.cloudflare.steamstatic.com/steam/apps/%s/%s" % (app_id, cdn[0])
        return ""

    @staticmethod
    def get_cdn_fallback_urls(app_id, asset_type):
        cdn = SteamAssets._CDN.get(asset_type, [])
        base = "https://cdn.cloudflare.steamstatic.com/steam/apps"
        return ["%s/%s/%s" % (base, app_id, p) for p in cdn]

    @staticmethod
    def save_custom_image(app_id, asset_type, url_or_path, db=None, source="steamgriddb"):
        # save image to Steam grid dir
        try:
            gdir = SteamAssets.get_steam_grid_path()

            sfx = SteamAssets._SUFFIXES.get(asset_type)
            if sfx is None:
                logger.info(t("logs.assets.unknown_type", type=asset_type))
                return False
            fname = "%s%s.png" % (app_id, sfx)
            target = gdir / fname

            # download URL
            if str(url_or_path).startswith("http"):
                hdrs = {"User-Agent": "SteamLibraryManager/1.0"}
                resp = requests.get(url_or_path, headers=hdrs, timeout=HTTP_TIMEOUT)
                if resp.status_code == 200:
                    with open(target, "wb") as f:
                        f.write(resp.content)
                    logger.info(t("logs.steamgrid.saved", type=asset_type, app_id=app_id))
                    logger.info(t("logs.assets.saved_to", path=target))

                    if db:
                        SteamAssets._save_meta(db, app_id, asset_type, target, source, str(url_or_path))
                    return True

            # copy local file
            elif os.path.exists(url_or_path):
                shutil.copy2(url_or_path, target)
                logger.info(t("logs.steamgrid.saved", type=asset_type, app_id=app_id))
                logger.info(t("logs.assets.saved_to", path=target))

                if db:
                    SteamAssets._save_meta(db, app_id, asset_type, target, source, None)
                return True

        except (OSError, requests.RequestException, ValueError) as e:
            logger.error(t("logs.steamgrid.save_error", error=e))
            return False

        return False

    @staticmethod
    def _save_meta(db, app_id, asset_type, fpath, source, src_url):
        # save artwork metadata to DB
        try:
            with open(fpath, "rb") as f:
                fhash = hashlib.sha256(f.read()).hexdigest()

            fsize = fpath.stat().st_size

            w, h = 0, 0
            try:
                from PIL import Image

                with Image.open(fpath) as img:
                    w, h = img.size
            except ImportError:
                pass

            db_type = SteamAssets.ASSET_TYPE_MAP.get(asset_type, asset_type)

            db.conn.execute(
                "INSERT OR REPLACE INTO custom_artwork"
                " (app_id, artwork_type, source, source_url, file_hash,"
                " file_size, width, height, set_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (int(app_id), db_type, source, src_url, fhash, fsize, w, h, int(time.time())),
            )
            db.commit()
            logger.debug("saved artwork meta: %s / %s" % (app_id, db_type))

        except Exception as e:
            logger.warning("could not save artwork meta: %s" % e)

    @staticmethod
    def delete_custom_image(app_id, asset_type, db=None):
        # remove custom image from grid dir
        try:
            gdir = SteamAssets.get_steam_grid_path()

            sfx = SteamAssets._SUFFIXES.get(asset_type)
            if sfx is None:
                return False
            target = gdir / ("%s%s.png" % (app_id, sfx))

            if target.exists():
                os.remove(target)
                logger.info(t("logs.steamgrid.deleted", path=target.name))

            if db:
                db_type = SteamAssets.ASSET_TYPE_MAP.get(asset_type, asset_type)
                db.conn.execute(
                    "DELETE FROM custom_artwork WHERE app_id = ? AND artwork_type = ?",
                    (int(app_id), db_type),
                )
                db.commit()

            return True

        except (OSError, ValueError) as e:
            logger.error(t("logs.steamgrid.delete_error", error=e))
            return False

    @staticmethod
    def export_artwork_package(db, export_dir):
        # export all custom artwork for sync
        art_dir = export_dir / "artwork"
        art_dir.mkdir(parents=True, exist_ok=True)

        gdir = SteamAssets.get_steam_grid_path()

        cur = db.conn.execute("SELECT * FROM custom_artwork ORDER BY app_id, artwork_type")

        manifest = {}
        stats = {"grid_p": 0, "grid_h": 0, "hero": 0, "logo": 0, "icon": 0}

        for row in cur.fetchall():
            aid = row["app_id"]
            atype = row["artwork_type"]
            fhash = row["file_hash"]

            sfx = SteamAssets._DB_SUFFIXES.get(atype)
            if sfx is None:
                continue
            src = gdir / ("%s%s.png" % (aid, sfx))

            if not src.exists():
                logger.warning("missing artwork: %s" % src)
                continue

            dest_name = "%s_%s_%s.png" % (aid, atype, fhash[:8])
            shutil.copy2(src, art_dir / dest_name)

            manifest["%s_%s" % (aid, atype)] = {
                "app_id": aid,
                "artwork_type": atype,
                "filename": dest_name,
                "hash": fhash,
                "source": row["source"],
                "source_url": row["source_url"],
                "width": row["width"],
                "height": row["height"],
                "set_at": row["set_at"],
            }

            stats[atype] += 1

        with open(export_dir / "artwork_manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info("exported %d artworks" % len(manifest))
        return stats

    @staticmethod
    def import_artwork_package(db, import_dir):
        # import artwork from another device
        mf = import_dir / "artwork_manifest.json"
        if not mf.exists():
            raise FileNotFoundError("manifest not found: %s" % mf)

        art_dir = import_dir / "artwork"
        if not art_dir.exists():
            raise FileNotFoundError("artwork folder not found: %s" % art_dir)

        with open(mf) as f:
            manifest = json.load(f)

        gdir = SteamAssets.get_steam_grid_path()
        stats = {"grid_p": 0, "grid_h": 0, "hero": 0, "logo": 0, "icon": 0}

        for _key, info in manifest.items():
            aid = info["app_id"]
            atype = info["artwork_type"]
            src = art_dir / info["filename"]

            if not src.exists():
                logger.warning("missing file: %s" % src)
                continue

            sfx = SteamAssets._DB_SUFFIXES.get(atype)
            if sfx is None:
                continue
            dest = gdir / ("%s%s.png" % (aid, sfx))

            shutil.copy2(src, dest)

            db.conn.execute(
                "INSERT OR REPLACE INTO custom_artwork"
                " (app_id, artwork_type, source, source_url, file_hash,"
                " file_size, width, height, set_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    aid,
                    atype,
                    info["source"],
                    info["source_url"],
                    info["hash"],
                    dest.stat().st_size,
                    info["width"],
                    info["height"],
                    info["set_at"],
                ),
            )

            stats[atype] += 1

        db.commit()
        logger.info("imported %d artworks" % len(manifest))
        return stats
