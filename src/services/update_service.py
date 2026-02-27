"""AppImage self-update service using GitHub Releases API.

Uses QNetworkAccessManager for non-blocking HTTP requests.
Only active when running as AppImage ($APPIMAGE set).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from src.utils.i18n import t
from src.version import __version__

__all__ = ["UpdateService", "UpdateInfo"]

logger = logging.getLogger("steamlibmgr.update")

_GITHUB_API_URL = "https://api.github.com/repos/Switch-Bros/SteamLibraryManager/releases/latest"


@dataclass(frozen=True)
class UpdateInfo:
    """Information about an available update.

    Args:
        version: New version string.
        download_url: Direct URL to AppImage asset.
        download_size: Size in bytes.
        release_notes: Markdown release notes.
        html_url: URL to GitHub release page.
    """

    version: str
    download_url: str
    download_size: int
    release_notes: str
    html_url: str


class UpdateService(QObject):
    """Checks for updates and manages AppImage update flow.

    Signals:
        update_available: Emitted with UpdateInfo when newer version found.
        update_not_available: Emitted when already on latest.
        check_failed: Emitted with error message.
        download_progress: Emitted with (downloaded_bytes, total_bytes).
        download_finished: Emitted with path to downloaded AppImage.
        download_failed: Emitted with error message.
    """

    update_available = pyqtSignal(object)
    update_not_available = pyqtSignal()
    check_failed = pyqtSignal(str)
    download_progress = pyqtSignal(int, int)
    download_finished = pyqtSignal(str)
    download_failed = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._download_reply: QNetworkReply | None = None
        self._download_path: Path | None = None

    @staticmethod
    def is_appimage() -> bool:
        """Check if running as AppImage."""
        return bool(os.environ.get("APPIMAGE"))

    @staticmethod
    def current_appimage_path() -> Path | None:
        """Get current AppImage path from $APPIMAGE."""
        appimage = os.environ.get("APPIMAGE")
        return Path(appimage) if appimage else None

    def check_for_update(self) -> None:
        """Check GitHub Releases for newer version. Non-blocking."""
        if not self.is_appimage():
            logger.info(t("logs.update.not_appimage"))
            self.check_failed.emit(t("update.not_appimage"))
            return

        request = QNetworkRequest(QUrl(_GITHUB_API_URL))
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader,
            f"SteamLibraryManager/{__version__}",
        )
        reply = self._nam.get(request)
        reply.finished.connect(lambda: self._on_check_finished(reply))

    def _on_check_finished(self, reply: QNetworkReply) -> None:
        """Handle GitHub API response."""
        if reply.error() != QNetworkReply.NetworkError.NoError:
            error_msg = reply.errorString()
            logger.warning(t("logs.update.check_failed", error=error_msg))
            self.check_failed.emit(error_msg)
            reply.deleteLater()
            return

        try:
            data = json.loads(bytes(reply.readAll()))
            reply.deleteLater()
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(t("logs.update.check_failed", error=str(e)))
            self.check_failed.emit(str(e))
            return

        available = data.get("tag_name", "").lstrip("v")
        if not self._is_newer(available):
            logger.info(t("logs.update.up_to_date", version=__version__))
            self.update_not_available.emit()
            return

        # Find AppImage asset
        download_url, download_size = "", 0
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".AppImage"):
                download_url = asset.get("browser_download_url", "")
                download_size = asset.get("size", 0)
                break

        if not download_url:
            self.check_failed.emit(t("update.no_appimage_asset"))
            return

        logger.info(t("logs.update.available", current=__version__, new=available))
        self.update_available.emit(
            UpdateInfo(
                version=available,
                download_url=download_url,
                download_size=download_size,
                release_notes=data.get("body", ""),
                html_url=data.get("html_url", ""),
            )
        )

    def download_update(self, info: UpdateInfo) -> None:
        """Download new AppImage with progress signals."""
        current = self.current_appimage_path()
        if not current:
            self.download_failed.emit(t("update.not_appimage"))
            return

        # Same filesystem for atomic replace
        self._download_path = current.parent / f".SLM_update_{info.version}.AppImage"

        request = QNetworkRequest(QUrl(info.download_url))
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader,
            f"SteamLibraryManager/{__version__}",
        )
        self._download_reply = self._nam.get(request)
        self._download_reply.downloadProgress.connect(lambda recv, total: self.download_progress.emit(recv, total))
        self._download_reply.finished.connect(self._on_download_finished)

    def _on_download_finished(self) -> None:
        """Write downloaded data to disk."""
        reply = self._download_reply
        if not reply or not self._download_path:
            return

        if reply.error() != QNetworkReply.NetworkError.NoError:
            error_msg = reply.errorString()
            logger.error(t("logs.update.download_failed", error=error_msg))
            self.download_failed.emit(error_msg)
            reply.deleteLater()
            return

        try:
            self._download_path.write_bytes(bytes(reply.readAll()))
            reply.deleteLater()
            self._download_path.chmod(0o755)
            logger.info(t("logs.update.download_complete", path=str(self._download_path)))
            self.download_finished.emit(str(self._download_path))
        except Exception as e:
            logger.error(t("logs.update.download_failed", error=str(e)))
            self.download_failed.emit(str(e))

    def cancel_download(self) -> None:
        """Cancel in-progress download."""
        if self._download_reply:
            self._download_reply.abort()
        if self._download_path and self._download_path.exists():
            self._download_path.unlink(missing_ok=True)

    @staticmethod
    def install_update(new_appimage_path: str) -> bool:
        """Atomically replace current AppImage and restart.

        IMPORTANT: Caller MUST save application state (collections,
        unsaved changes) and show a confirm dialog BEFORE calling this!
        This method has no access to MainWindow or save logic.

        Args:
            new_appimage_path: Path to downloaded new AppImage.

        Returns:
            False on failure (rolled back). Never returns on success (execv).
        """
        current = UpdateService.current_appimage_path()
        new_path = Path(new_appimage_path)
        if not current or not current.exists():
            return False

        backup = current.with_suffix(".bak")
        try:
            shutil.copy2(current, backup)
            new_path.chmod(0o755)
            new_path.replace(current)
            logger.info(t("logs.update.installing", path=str(current)))
            os.execv(str(current), [str(current)])
        except Exception as e:
            logger.error(t("logs.update.install_failed", error=str(e)))
            if backup.exists():
                backup.replace(current)
            return False
        return True  # pragma: no cover — execv replaces the process

    @staticmethod
    def _is_newer(available: str) -> bool:
        """Compare versions using semantic versioning."""
        try:
            from packaging.version import Version

            return Version(available) > Version(__version__)
        except Exception:
            return available != __version__
