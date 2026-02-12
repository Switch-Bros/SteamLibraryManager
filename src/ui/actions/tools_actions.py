from __future__ import annotations

from typing import TYPE_CHECKING
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QProgressDialog, QApplication
import requests

from src.utils.i18n import t
from src.ui.widgets.ui_helper import UIHelper
from src.ui.missing_metadata_dialog import MissingMetadataDialog
from src.core.game_manager import Game

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

class StoreCheckThread(QThread):
    """Background thread to check Steam Store availability."""
    finished = pyqtSignal(str, str)

    def __init__(self, app_id: str):
        super().__init__()
        self.app_id = app_id

    def run(self):
        """Performs the store check via HTTP request."""
        try:
            url = f"https://store.steampowered.com/app/{self.app_id}/"
            # User-Agent is important to avoid immediate blocking
            response = requests.get(url, timeout=10, allow_redirects=False, headers={'User-Agent': 'SLM/1.0'})

            if response.status_code == 200:
                text_lower = response.text.lower()

                # Check for geo-blocking keywords
                if ('not available in your country' in text_lower or
                        'nicht in ihrem land' in text_lower or
                        'not available in your region' in text_lower or
                        'currently not' in text_lower or
                        'not available' in text_lower):
                    self.finished.emit('geo_locked', f"{t('emoji.blocked')} {t('ui.store_check.geo_locked')}")
                # Check for age gate
                elif 'agecheck' in text_lower:
                    self.finished.emit('age_gate', t('ui.store_check.age_gate'))
                # Check for valid store page indicators
                elif 'app_header' in text_lower or 'game_area_purchase' in text_lower:
                    self.finished.emit('available', f"{t('emoji.success')} {t('ui.store_check.available')}")
                else:
                    self.finished.emit('delisted', f"{t('emoji.error')} {t('ui.store_check.delisted')}")

            elif response.status_code == 302:
                # Handle redirects (often implies age gate or delisted)
                redirect_url = response.headers.get('Location', '')
                if 'agecheck' in redirect_url:
                    self.finished.emit('age_gate', t('ui.store_check.age_gate'))
                else:
                    self.finished.emit('delisted', f"{t('emoji.error')} {t('ui.store_check.delisted')}")

            elif response.status_code in [404, 403]:
                self.finished.emit('delisted', f"{t('emoji.error')} {t('ui.store_check.removed')}")
            else:
                self.finished.emit('unknown',
                                   f"{t('emoji.unknown')} {t('ui.store_check.unknown', code=response.status_code)}")

        except Exception as ex:
            self.finished.emit('unknown', str(ex))

class ToolsActions:
    """Handles tool-related actions like metadata search and store checks."""

    def __init__(self, main_window: 'MainWindow'):
        self.main_window = main_window
        self._store_check_thread: StoreCheckThread | None = None

    def find_missing_metadata(self) -> None:
        """Shows a dialog listing games with incomplete metadata."""
        if not self.main_window.metadata_service:
            return

        affected = self.main_window.metadata_service.find_missing_metadata()

        if affected:
            dialog = MissingMetadataDialog(self.main_window, affected)
            dialog.exec()
        else:
            UIHelper.show_success(self.main_window, t('ui.tools.missing_metadata.all_complete'))

    def check_store_availability(self, game: Game) -> None:
        """Checks if a game is still available on the Steam Store.

        Args:
            game: The game object to check.
        """
        # Create and show progress dialog
        progress = QProgressDialog(t('ui.store_check.checking'), None, 0, 0, self.main_window)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle(t('ui.store_check.title'))
        progress.show()
        QApplication.processEvents()

        # Define callback for thread completion
        def on_check_finished(status: str, details: str):
            progress.close()
            title = t('ui.store_check.title')
            msg = f"{game.name}: {details}"

            if status == 'available':
                UIHelper.show_success(self.main_window, msg, title)
            elif status == 'age_gate':
                UIHelper.show_info(self.main_window, msg, title)
            else:
                UIHelper.show_warning(self.main_window, msg, title)

        # Start background thread
        self._store_check_thread = StoreCheckThread(game.app_id)
        # noinspection PyUnresolvedReferences
        self._store_check_thread.finished.connect(on_check_finished)
        self._store_check_thread.start()