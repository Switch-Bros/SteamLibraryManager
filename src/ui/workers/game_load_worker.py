"""
Worker thread for loading games in the background.

This module contains the GameLoadWorker thread that handles game loading
asynchronously without blocking the UI.
"""
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, pyqtSignal

if TYPE_CHECKING:
    from src.services.game_service import GameService


class GameLoadWorker(QThread):
    """Background thread for loading games without blocking the UI.

    Loads game data from Steam API and local files in a separate thread,
    emitting progress updates that can be displayed in a progress dialog.

    Attributes:
        game_service: The GameService instance to use for loading.
        user_id: The Steam user ID to load games for.

    Signals:
        progress_update: Emitted during loading with (step_name, current, total).
        finished: Emitted when loading completes with success status.
    """

    progress_update = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool)

    def __init__(self, game_service: 'GameService', user_id: str):
        """Initializes the game load worker.

        Args:
            game_service: The GameService instance to use for loading.
            user_id: The Steam user ID to load games for.
        """
        super().__init__()
        self.game_service = game_service
        self.user_id = user_id

    def run(self) -> None:
        """Executes the game loading process.

        Calls the game service's load_games method with a progress callback
        and emits the finished signal with the result.
        """

        def progress_callback(step: str, current: int, total: int):
            self.progress_update.emit(step, current, total)

        success = self.game_service.load_games(self.user_id, progress_callback)
        self.finished.emit(success)
