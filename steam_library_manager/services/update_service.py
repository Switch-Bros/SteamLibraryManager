#
# steam_library_manager/services/update_service.py
# GitHub release update checker and AppImage updater
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from steam_library_manager.utils.desktop_integration import (
    install_desktop_entry,
    is_desktop_entry_installed,
)
from steam_library_manager.utils.i18n import t
from steam_library_manager.version import __version__

__all__ = ["UpdateService", "UpdateInfo"]

logger = logging.getLogger("steamlibmgr.update")

_GH_URL = "https://api.github.com/repos/Switch-Bros/SteamLibraryManager/releases/latest"


@dataclass(frozen=True)
class UpdateInfo:
    """Update metadata."""

    version: str
    download_url: str
    download_size: int
    release_notes: str
    html_url: str


class UpdateService(QObject):
    """Checks GitHub for updates, downloads + installs AppImages."""

    update_available = pyqtSignal(object)
    update_not_available = pyqtSignal()
    check_failed = pyqtSignal(str)
    download_progress = pyqtSignal(int, int)
    download_finished = pyqtSignal(str)
    download_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._net = QNetworkAccessManager(self)
        self._r = None  # current reply
        self._p = None  # download path

    @staticmethod
    def is_appimage():
        return bool(os.environ.get("APPIMAGE"))

    @staticmethod
    def current_appimage_path():
        ai = os.environ.get("APPIMAGE")
        return Path(ai) if ai else None

    def check_for_update(self):
        # check GH for updates
        if not self.is_appimage():
            logger.info(t("logs.update.not_appimage"))
            self.check_failed.emit(t("update.not_appimage"))
            return

        req = QNetworkRequest(QUrl(_GH_URL))
        req.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader,
            "SteamLibraryManager/%s" % __version__,
        )
        reply = self._net.get(req)
        if reply:
            reply.finished.connect(lambda: self._on_check(reply))

    def _on_check(self, reply):
        # parse GH response
        if reply.error() != QNetworkReply.NetworkError.NoError:
            msg = reply.errorString()
            logger.warning(t("logs.update.check_failed", error=msg))
            self.check_failed.emit(msg)
            reply.deleteLater()
            return

        try:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            reply.deleteLater()
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(t("logs.update.check_failed", error=str(e)))
            self.check_failed.emit(str(e))
            return

        avail = data.get("tag_name", "").lstrip("v")
        if not self._is_newer(avail):
            logger.info(t("logs.update.up_to_date", version=__version__))
            self.update_not_available.emit()
            return

        # find AppImage
        url, size = "", 0
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".AppImage"):
                url = asset.get("browser_download_url", "")
                size = asset.get("size", 0)
                break

        if not url:
            self.check_failed.emit(t("update.no_appimage_asset"))
            return

        logger.info(t("logs.update.available", current=__version__, new=avail))
        self.update_available.emit(
            UpdateInfo(
                version=avail,
                download_url=url,
                download_size=size,
                release_notes=data.get("body", ""),
                html_url=data.get("html_url", ""),
            )
        )

    def download_update(self, info):
        # download with progress
        cur = self.current_appimage_path()
        if not cur:
            self.download_failed.emit(t("update.not_appimage"))
            return

        self._p = cur.parent / ".SLM_update.AppImage"

        req = QNetworkRequest(QUrl(info.download_url))
        req.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader,
            "SteamLibraryManager/%s" % __version__,
        )
        self._r = self._net.get(req)
        if self._r:
            self._r.downloadProgress.connect(lambda recv, tot: self.download_progress.emit(recv, tot))
            self._r.finished.connect(self._on_dl)

    def _on_dl(self):
        # write to disk
        reply = self._r
        if not reply or not self._p:
            return

        if reply.error() != QNetworkReply.NetworkError.NoError:
            msg = reply.errorString()
            logger.error(t("logs.update.download_failed", error=msg))
            self.download_failed.emit(msg)
            reply.deleteLater()
            return

        try:
            self._p.write_bytes(reply.readAll().data())
            reply.deleteLater()
            self._p.chmod(0o755)
            logger.info(t("logs.update.download_complete", path=str(self._p)))
            self.download_finished.emit(str(self._p))
        except Exception as e:
            logger.error(t("logs.update.download_failed", error=str(e)))
            self.download_failed.emit(str(e))

    def cancel_download(self):
        if self._r:
            self._r.abort()
        if self._p and self._p.exists():
            self._p.unlink(missing_ok=True)

    @staticmethod
    def install_update(new_path):
        # atomic replace + restart
        cur = UpdateService.current_appimage_path()
        new = Path(new_path)
        if not cur or not cur.exists():
            return False

        bak = cur.with_suffix(".bak")
        try:
            shutil.copy2(cur, bak)
            new.chmod(0o755)
            new.replace(cur)

            if is_desktop_entry_installed():
                install_desktop_entry()

            logger.info(t("logs.update.installing", path=str(cur)))
            os.execv(str(cur), [str(cur)])
        except Exception as e:
            logger.error(t("logs.update.install_failed", error=str(e)))
            if bak.exists():
                bak.replace(cur)
            return False
        return True  # pragma: no cover

    @staticmethod
    def _is_newer(v):
        # semver compare
        try:
            from packaging.version import Version

            return Version(v) > Version(__version__)
        except Exception:
            return v != __version__
