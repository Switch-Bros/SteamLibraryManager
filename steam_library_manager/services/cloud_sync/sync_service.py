#
# steam_library_manager/services/cloud_sync/sync_service.py
# Core sync orchestration - upload, download, conflict detection
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: add progress callbacks for large transfers

from __future__ import annotations

import hashlib
import logging
import shutil
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from steam_library_manager.services.cloud_sync.provider import CloudProvider

logger = logging.getLogger(__name__)

# remote directory prefix
_REMOTE_DIR = "SteamLibraryManager"
_REMOTE_DB = "%s/metadata.db" % _REMOTE_DIR
_REMOTE_SETTINGS = "%s/settings.json" % _REMOTE_DIR
_REMOTE_COLLECTIONS = "%s/cloud-storage-namespace-1.json" % _REMOTE_DIR


class ConflictAction(Enum):
    """Outcome of a conflict detection check."""

    NONE = "none"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    CONFLICT = "conflict"


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    message: str


class CloudSyncService:
    """Orchestrates upload, download, and conflict detection."""

    def __init__(
        self,
        provider: CloudProvider,
        db_path: Path,
        settings_path: Path,
        tmp_dir: Path,
        collections_path: Path | None = None,
    ) -> None:
        self._prov = provider
        self._db = db_path
        self._settings = settings_path
        self._tmp = tmp_dir
        self._collections = collections_path

    # -- public api --

    def upload(self) -> SyncResult:
        # bail if not connected
        if not self._prov.is_connected():
            logger.warning("upload failed: provider not connected")
            return SyncResult(False, "not connected")

        self._tmp.mkdir(parents=True, exist_ok=True)
        snap = self._tmp / "metadata.db"

        try:
            # sqlite3.backup for consistent snapshot (never shutil.copy on open db)
            src_conn = sqlite3.connect(str(self._db))
            dst_conn = sqlite3.connect(str(snap))
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()

            # upload db snapshot
            ok = self._prov.upload_file(snap, _REMOTE_DB)
            if not ok:
                return SyncResult(False, "db upload failed")

            # upload settings if it exists
            if self._settings.exists():
                ok = self._prov.upload_file(self._settings, _REMOTE_SETTINGS)
                if not ok:
                    return SyncResult(False, "settings upload failed")

            # upload Steam collections (cloud-storage-namespace-1.json)
            if self._collections and self._collections.exists():
                ok = self._prov.upload_file(self._collections, _REMOTE_COLLECTIONS)
                if not ok:
                    logger.warning("collections upload failed, continuing")

            cs = self._sha256(snap)
            logger.info("upload complete, checksum=%s" % cs)
            return SyncResult(True, cs)
        except Exception as exc:
            logger.error("upload error: %s" % exc)
            return SyncResult(False, str(exc))
        finally:
            # cleanup temp snapshot
            if snap.exists():
                snap.unlink()

    def download(self) -> SyncResult:
        # bail if not connected
        if not self._prov.is_connected():
            logger.warning("download failed: provider not connected")
            return SyncResult(False, "not connected")

        # check remote exists
        info = self._prov.get_file_info(_REMOTE_DB)
        if info is None:
            return SyncResult(False, "no remote db found")

        self._tmp.mkdir(parents=True, exist_ok=True)
        tmp_db = self._tmp / "metadata.db"
        tmp_settings = self._tmp / "settings.json"

        try:
            # download db
            ok = self._prov.download_file(_REMOTE_DB, tmp_db)
            if not ok:
                return SyncResult(False, "db download failed")

            # verify checksum
            cs = self._sha256(tmp_db)
            if cs != info.checksum:
                return SyncResult(False, "checksum mismatch")

            # replace local files
            shutil.copy2(tmp_db, self._db)

            # download settings if available
            if self._prov.get_file_info(_REMOTE_SETTINGS) is not None:
                ok = self._prov.download_file(_REMOTE_SETTINGS, tmp_settings)
                if ok:
                    shutil.copy2(tmp_settings, self._settings)

            # download Steam collections if available and target path known
            if self._collections:
                remote_col = self._prov.get_file_info(_REMOTE_COLLECTIONS)
                if remote_col is not None:
                    tmp_col = self._tmp / "cloud-storage-namespace-1.json"
                    ok = self._prov.download_file(_REMOTE_COLLECTIONS, tmp_col)
                    if ok:
                        self._collections.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(tmp_col, self._collections)
                        logger.info(
                            "collections downloaded (%d bytes) to %s" % (tmp_col.stat().st_size, self._collections)
                        )
                        if tmp_col.exists():
                            tmp_col.unlink()
                    else:
                        logger.error("collections download failed")
                else:
                    logger.warning("no remote collections found on cloud")
            else:
                logger.warning("no collections_path set, skipping collections sync")

            logger.info("download complete, checksum=%s" % cs)
            return SyncResult(True, cs)
        except Exception as exc:
            logger.error("download error: %s" % exc)
            return SyncResult(False, str(exc))
        finally:
            # cleanup
            if tmp_db.exists():
                tmp_db.unlink()
            if tmp_settings.exists():
                tmp_settings.unlink()

    def detect_conflict(self, last_cs: str) -> ConflictAction:
        # compute local checksum via backup snapshot (consistent with upload)
        local_cs = self._snapshot_checksum() if self._db.exists() else ""

        # get remote checksum
        info = self._prov.get_file_info(_REMOTE_DB)
        if info is None:
            # no remote -> should upload
            return ConflictAction.UPLOAD

        remote_cs = info.checksum
        local_changed = local_cs != last_cs
        remote_changed = remote_cs != last_cs

        if not local_changed and not remote_changed:
            return ConflictAction.NONE
        if local_changed and not remote_changed:
            return ConflictAction.UPLOAD
        if not local_changed and remote_changed:
            return ConflictAction.DOWNLOAD
        # both changed
        return ConflictAction.CONFLICT

    # -- helpers --

    def _snapshot_checksum(self) -> str:
        # create a backup snapshot and hash it (matches what upload produces)
        self._tmp.mkdir(parents=True, exist_ok=True)
        snap = self._tmp / "_conflict_check.db"
        try:
            src = sqlite3.connect(str(self._db))
            dst = sqlite3.connect(str(snap))
            src.backup(dst)
            dst.close()
            src.close()
            return self._sha256(snap)
        finally:
            if snap.exists():
                snap.unlink()

    @staticmethod
    def _sha256(path: Path) -> str:
        # chunked read for large files
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
