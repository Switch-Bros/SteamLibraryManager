#
# steam_library_manager/services/cloud_sync/rclone.py
# Cloud provider via rclone CLI (supports 70+ backends)
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: add progress parsing from rclone output?

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from steam_library_manager.core.logging import logger
from steam_library_manager.services.cloud_sync.provider import CloudProvider, FileInfo

__all__ = ["RcloneProvider"]

_TIMEOUT = 60  # seconds per rclone command


class RcloneProvider(CloudProvider):
    """Cloud provider via rclone CLI subprocess calls."""

    def __init__(self, remote: str) -> None:
        # remote is the rclone remote name, e.g. "mega:" or "nextcloud:"
        self._remote = remote.rstrip("/")
        if not self._remote.endswith(":"):
            self._remote += ":"
        self._connected = False

    # -- connection --

    def connect(self) -> bool:
        # verify rclone is installed and remote exists
        if not self._rclone_installed():
            logger.error("rclone not found in PATH")
            return False

        # check remote is configured
        try:
            out = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True, timeout=10)
            remotes = [r.strip() for r in out.stdout.strip().splitlines()]
            if self._remote not in remotes:
                logger.error("rclone remote '%s' not configured" % self._remote)
                return False
        except Exception as exc:
            logger.error("rclone listremotes failed: %s" % exc)
            return False

        self._connected = True
        logger.info("rclone connected to %s" % self._remote)
        return True

    def disconnect(self) -> None:
        self._connected = False
        logger.info("rclone disconnected")

    def is_connected(self) -> bool:
        return self._connected

    # -- upload --

    def upload_file(self, local: Path, remote_name: str) -> bool:
        if not self.is_connected():
            return False
        try:
            dst = "%s%s" % (self._remote, remote_name)
            result = subprocess.run(
                ["rclone", "copyto", str(local), dst],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
            if result.returncode != 0:
                logger.error("rclone upload failed: %s" % result.stderr.strip())
                return False
            logger.info("rclone uploaded %s -> %s" % (local.name, dst))
            return True
        except subprocess.TimeoutExpired:
            logger.error("rclone upload timed out")
            return False
        except Exception as exc:
            logger.error("rclone upload error: %s" % exc)
            return False

    # -- download --

    def download_file(self, remote_name: str, local: Path) -> bool:
        if not self.is_connected():
            return False
        try:
            src = "%s%s" % (self._remote, remote_name)
            local.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["rclone", "copyto", src, str(local)],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
            if result.returncode != 0:
                logger.error("rclone download failed: %s" % result.stderr.strip())
                return False
            logger.info("rclone downloaded %s -> %s" % (src, local))
            return True
        except subprocess.TimeoutExpired:
            logger.error("rclone download timed out")
            return False
        except Exception as exc:
            logger.error("rclone download error: %s" % exc)
            return False

    # -- metadata --

    def get_file_info(self, remote_name: str) -> FileInfo | None:
        if not self.is_connected():
            return None
        try:
            src = "%s%s" % (self._remote, remote_name)
            result = subprocess.run(
                ["rclone", "lsjson", src],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
            if result.returncode != 0:
                return None

            items = json.loads(result.stdout)
            if not items:
                return None

            item = items[0]
            sz = item.get("Size", 0)

            # rclone can compute hashes natively
            cs = self._remote_checksum(remote_name)

            return FileInfo(
                name=remote_name,
                size=sz,
                modified=0.0,
                checksum=cs,
            )
        except Exception as exc:
            logger.error("rclone get_file_info error: %s" % exc)
            return None

    # -- helpers --

    def _remote_checksum(self, remote_name: str) -> str:
        # try rclone hashsum sha256
        try:
            src = "%s%s" % (self._remote, remote_name)
            result = subprocess.run(
                ["rclone", "hashsum", "sha256", src],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
            if result.returncode == 0 and result.stdout.strip():
                # output format: "hash  filename"
                return result.stdout.strip().split()[0]
        except Exception:
            pass

        # fallback: download to temp and hash locally
        import tempfile

        tmp = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                tmp = Path(f.name)
            if self.download_file(remote_name, tmp):
                h = hashlib.sha256()
                with open(tmp, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                return h.hexdigest()
        except Exception:
            pass
        finally:
            if tmp is not None and tmp.exists():
                tmp.unlink()
        return ""

    @staticmethod
    def _rclone_installed() -> bool:
        try:
            result = subprocess.run(
                ["rclone", "version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def list_remotes() -> list[str]:
        # list configured rclone remotes (for UI dropdown)
        try:
            result = subprocess.run(
                ["rclone", "listremotes"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return [r.strip() for r in result.stdout.strip().splitlines() if r.strip()]
        except Exception:
            pass
        return []
