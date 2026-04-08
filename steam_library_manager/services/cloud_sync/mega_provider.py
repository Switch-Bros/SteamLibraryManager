#
# steam_library_manager/services/cloud_sync/mega_provider.py
# MEGA cloud provider using mega.py
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: add progress callback for large uploads/downloads

from __future__ import annotations

import hashlib
import logging
import tempfile
from pathlib import Path

from steam_library_manager.services.cloud_sync.provider import CloudProvider, FileInfo

logger = logging.getLogger(__name__)

# optional dependency - graceful fallback
try:
    from mega import Mega
except ImportError:
    Mega = None  # type: ignore[assignment,misc]

# remote folder name on MEGA
_DIR_NAME = "SteamLibraryManager"

# skip checksum for files bigger than this
_MAX_HASH_SIZE = 50 * 1024 * 1024  # 50 MB


class MegaProvider(CloudProvider):
    """MEGA storage backend via mega.py."""

    def __init__(self, email: str, password: str) -> None:
        self._email = email
        self._pw = password
        self._mega: Mega | None = None  # type: ignore[assignment]
        self._connected = False

    # -- connection --

    def connect(self) -> bool:
        if Mega is None:
            logger.error("mega.py not installed")
            return False
        try:
            m = Mega()
            self._mega = m.login(self._email, self._pw)
            self._connected = True
            logger.info("mega connected for %s" % self._email)
            return True
        except Exception as exc:
            logger.error("mega connect failed: %s" % exc)
            self._mega = None
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._mega = None
        self._connected = False
        logger.info("mega disconnected")

    def is_connected(self) -> bool:
        return self._connected and self._mega is not None

    # -- upload --

    def upload_file(self, local: Path, remote_name: str) -> bool:
        if not self.is_connected():
            return False
        try:
            folder_handle = self._find_or_create_folder()
            if folder_handle is None:
                return False

            # delete existing file with same name before upload
            fname = remote_name.split("/")[-1]
            existing = self._mega.find(fname)  # type: ignore[union-attr]
            if existing:
                # find() returns (handle_str, node_dict)
                self._mega.delete(existing[0])  # type: ignore[union-attr]

            self._mega.upload(str(local), folder_handle)  # type: ignore[union-attr]
            logger.info("mega uploaded %s -> %s" % (local.name, remote_name))
            return True
        except Exception as exc:
            logger.error("mega upload failed: %s" % exc)
            return False

    # -- download --

    def download_file(self, remote_name: str, local: Path) -> bool:
        if not self.is_connected():
            return False
        try:
            fname = remote_name.split("/")[-1]
            found = self._mega.find(fname)  # type: ignore[union-attr]
            if not found:
                logger.error("mega file not found: %s" % fname)
                return False

            # find() returns (handle_str, node_dict)
            local.parent.mkdir(parents=True, exist_ok=True)
            self._mega.download(  # type: ignore[union-attr]
                found,
                dest_path=str(local.parent),
                dest_filename=local.name,
            )
            logger.info("mega downloaded %s -> %s" % (fname, local))
            return True
        except Exception as exc:
            logger.error("mega download failed: %s" % exc)
            return False

    # -- metadata --

    def get_file_info(self, remote_name: str) -> FileInfo | None:
        if not self.is_connected():
            return None
        try:
            fname = remote_name.split("/")[-1]
            found = self._mega.find(fname)  # type: ignore[union-attr]
            if not found:
                return None

            # find() returns (handle_str, node_dict)
            _handle, node = found
            sz = node.get("s", 0)

            # compute checksum by downloading to temp (mega has no native sha256)
            cs = ""
            if sz <= _MAX_HASH_SIZE:
                cs = self._remote_checksum(found[0])

            return FileInfo(
                name=remote_name,
                size=sz,
                modified=node.get("ts", 0.0),
                checksum=cs,
            )
        except Exception as exc:
            logger.error("mega get_file_info failed: %s" % exc)
            return None

    # -- private helpers --

    def _find_or_create_folder(self) -> str | None:
        # find existing folder or create it, returns handle string
        found = self._mega.find(_DIR_NAME)  # type: ignore[union-attr]
        if found:
            # find() returns (handle_str, node_dict) for folders
            return found[0]
        # create and return handle
        result = self._mega.create_folder(_DIR_NAME)  # type: ignore[union-attr]
        return result.get(_DIR_NAME) if result else None

    def _remote_checksum(self, file_node: tuple) -> str:
        # download to temp file and hash
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
            self._mega.download(  # type: ignore[union-attr]
                file_node,
                dest_path=str(tmp_path.parent),
                dest_filename=tmp_path.name,
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
            logger.error("mega checksum failed: %s" % exc)
            return ""
        finally:
            try:
                if tmp_path is not None:
                    tmp_path.unlink()
            except Exception:
                pass
