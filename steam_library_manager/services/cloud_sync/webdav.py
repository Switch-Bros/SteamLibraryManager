#
# steam_library_manager/services/cloud_sync/webdav.py
# WebDAV cloud provider using webdavclient3
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: add certificate pinning for self-signed servers
# TODO: add timeout configuration

from __future__ import annotations

import hashlib
import logging
import tempfile
from pathlib import Path

from steam_library_manager.services.cloud_sync.provider import CloudProvider, FileInfo

logger = logging.getLogger(__name__)

# optional dependency - graceful fallback
try:
    from webdav3.client import Client
except ImportError:
    Client = None  # type: ignore[assignment,misc]

# skip checksum for files bigger than this (too expensive over the wire)
_MAX_HASH_SIZE = 50 * 1024 * 1024  # 50 MB


class WebDAVProvider(CloudProvider):
    """WebDAV storage backend via webdavclient3."""

    def __init__(self, url: str, username: str, password: str) -> None:
        self._url = url
        self._user = username
        self._pw = password
        self._client: Client | None = None  # type: ignore[assignment]

    # -- connection --

    def connect(self) -> bool:
        if Client is None:
            logger.error("webdavclient3 not installed")
            return False
        try:
            opts = {
                "webdav_hostname": self._url,
                "webdav_login": self._user,
                "webdav_password": self._pw,
            }
            self._client = Client(opts)
            self._client.check()
            logger.info("webdav connected to %s" % self._url)
            return True
        except Exception as exc:
            logger.error("webdav connect failed: %s" % exc)
            self._client = None
            return False

    def disconnect(self) -> None:
        self._client = None
        logger.info("webdav disconnected")

    def is_connected(self) -> bool:
        return self._client is not None

    # -- upload --

    def upload_file(self, local: Path, remote_name: str) -> bool:
        if self._client is None:
            return False
        try:
            # ensure parent directory exists on server
            rdir = str(Path(remote_name).parent)
            if rdir and rdir != ".":
                self._ensure_dir(rdir)
            self._client.upload_sync(
                remote_path=remote_name,
                local_path=str(local),
            )
            logger.info("uploaded %s -> %s" % (local.name, remote_name))
            return True
        except Exception as exc:
            logger.error("webdav upload failed: %s" % exc)
            return False

    # -- download --

    def download_file(self, remote_name: str, local: Path) -> bool:
        if self._client is None:
            return False
        try:
            local.parent.mkdir(parents=True, exist_ok=True)
            self._client.download_sync(
                remote_path=remote_name,
                local_path=str(local),
            )
            logger.info("downloaded %s -> %s" % (remote_name, local))
            return True
        except Exception as exc:
            logger.error("webdav download failed: %s" % exc)
            return False

    # -- metadata --

    def get_file_info(self, remote_name: str) -> FileInfo | None:
        if self._client is None:
            return None
        try:
            if not self._client.check(remote_name):
                return None
            info = self._client.info(remote_name)
            sz = int(info.get("size", 0))
            mod = float(info.get("modified", 0))

            # compute checksum by downloading to temp (webdav has no native sha256)
            cs = ""
            if sz <= _MAX_HASH_SIZE:
                cs = self._remote_checksum(remote_name)

            return FileInfo(
                name=remote_name,
                size=sz,
                modified=mod,
                checksum=cs,
            )
        except Exception as exc:
            logger.error("webdav get_file_info failed: %s" % exc)
            return None

    # -- private helpers --

    def _ensure_dir(self, rdir: str) -> None:
        # create directory tree on remote, ignore if exists
        parts = Path(rdir).parts
        cur = ""
        for p in parts:
            cur = "%s/%s" % (cur, p) if cur else p
            try:
                if not self._client.check(cur):  # type: ignore[union-attr]
                    self._client.mkdir(cur)  # type: ignore[union-attr]
            except Exception:
                pass  # best effort

    def _remote_checksum(self, remote_name: str) -> str:
        # download to temp file and hash
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
            self._client.download_sync(  # type: ignore[union-attr]
                remote_path=remote_name,
                local_path=str(tmp_path),
            )
            h = hashlib.sha256()
            with open(tmp_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except Exception as exc:
            logger.error("webdav checksum failed: %s" % exc)
            return ""
        finally:
            try:
                if tmp_path is not None:
                    tmp_path.unlink()
            except Exception:
                pass
