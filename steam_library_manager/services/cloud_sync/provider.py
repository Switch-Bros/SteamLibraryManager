#
# steam_library_manager/services/cloud_sync/provider.py
# Cloud provider interface and file metadata
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: add list_files() once we need directory browsing

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileInfo:
    """Immutable metadata for a remote file."""

    name: str
    size: int
    modified: float
    checksum: str


class CloudProvider:
    """Base interface for cloud storage backends."""

    def connect(self) -> bool:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError

    def is_connected(self) -> bool:
        raise NotImplementedError

    # upload stuff

    def upload_file(self, local: Path, remote_name: str) -> bool:
        raise NotImplementedError

    # download stuff

    def download_file(self, remote_name: str, local: Path) -> bool:
        raise NotImplementedError

    # metadata

    def get_file_info(self, remote_name: str) -> FileInfo | None:
        raise NotImplementedError
